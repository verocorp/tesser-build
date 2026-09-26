package experiment

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os/exec"
	"strings"
	"time"
)

const stderrLimit = 16 << 10

type boundedOutput struct {
	buffer    bytes.Buffer
	limit     int
	truncated bool
}

func (output *boundedOutput) Write(data []byte) (int, error) {
	count := len(data)
	remaining := output.limit - output.buffer.Len()
	if count > remaining {
		output.truncated = true
		data = data[:remaining]
	}
	output.buffer.Write(data)
	return count, nil
}

func runStage(ctx context.Context, directory string, argv []string, kind, id string, inputs []json.RawMessage, expected []json.RawMessage) StageResult {
	stage := StageResult{Kind: kind, ID: id, Status: Correct, StartedAt: time.Now().UTC()}
	var input bytes.Buffer
	for _, message := range inputs {
		var compact bytes.Buffer
		json.Compact(&compact, message)
		input.Write(compact.Bytes())
		input.WriteByte('\n')
	}
	stdout := boundedOutput{limit: maxJSONBytes}
	stderr := boundedOutput{limit: stderrLimit}
	command := exec.CommandContext(ctx, argv[0], argv[1:]...)
	command.Dir = directory
	command.Stdin = &input
	command.Stdout = &stdout
	command.Stderr = &stderr
	command.WaitDelay = 100 * time.Millisecond
	configureProcessGroup(command)
	err := command.Start()
	if err == nil {
		err = command.Wait()
		killProcessGroup(command)
		exitCode := command.ProcessState.ExitCode()
		stage.ExitCode = &exitCode
	}
	stage.EndedAt = time.Now().UTC()
	stage.ElapsedMS = stage.EndedAt.Sub(stage.StartedAt).Milliseconds()
	stage.Stderr = stderr.buffer.String()
	stage.StderrTruncated = stderr.truncated
	if err != nil {
		stage.Error = err.Error()
		var exitError *exec.ExitError
		switch {
		case errors.Is(ctx.Err(), context.DeadlineExceeded):
			stage.Status = Timeout
		case errors.As(err, &exitError):
			stage.Status = Incorrect
		default:
			stage.Status = InfraError
		}
		return stage
	}
	if ctx.Err() != nil {
		stage.Status = contextStatus(ctx)
		stage.Error = ctx.Err().Error()
		return stage
	}
	if kind == "gate" {
		return stage
	}
	if stdout.truncated {
		stage.Status = Incorrect
		stage.Error = fmt.Sprintf("stdout exceeds %d bytes", maxJSONBytes)
		return stage
	}
	data := stdout.buffer.Bytes()
	lines := bytes.Split(data, []byte{'\n'})
	if len(data) == 0 {
		lines = nil
	} else if data[len(data)-1] == '\n' {
		lines = lines[:len(lines)-1]
	}
	stage.Responses = len(lines)
	if len(lines) != len(expected) {
		stage.Status = Incorrect
		stage.Error = fmt.Sprintf("response count: got %d, want %d", len(lines), len(expected))
		return stage
	}
	for index, line := range lines {
		actual, err := jsonObject(line)
		if err != nil {
			stage.Status = Incorrect
			stage.Error = fmt.Sprintf("response %d is not a valid JSON object: %v", index+1, err)
			return stage
		}
		wanted, err := jsonObject(expected[index])
		if err != nil {
			stage.Status = InfraError
			stage.Error = "invalid expected response"
			return stage
		}
		if !equalJSON(actual, wanted) {
			stage.Status = Incorrect
			stage.Error = fmt.Sprintf("response %d differs from the contract", index+1)
			return stage
		}
	}
	return stage
}

func equalJSON(left, right any) bool {
	switch value := left.(type) {
	case map[string]any:
		other, ok := right.(map[string]any)
		if !ok || len(value) != len(other) {
			return false
		}
		for key, item := range value {
			otherItem, exists := other[key]
			if !exists || !equalJSON(item, otherItem) {
				return false
			}
		}
		return true
	case []any:
		other, ok := right.([]any)
		if !ok || len(value) != len(other) {
			return false
		}
		for index, item := range value {
			if !equalJSON(item, other[index]) {
				return false
			}
		}
		return true
	case json.Number:
		other, ok := right.(json.Number)
		return ok && normalizeNumber(value) == normalizeNumber(other)
	default:
		return left == right
	}
}

func normalizeNumber(number json.Number) string {
	text := strings.ToLower(string(number))
	parts := strings.SplitN(text, "e", 2)
	exponent := new(big.Int)
	if len(parts) == 2 {
		exponent.SetString(parts[1], 10)
	}
	mantissa := parts[0]
	sign := ""
	if strings.HasPrefix(mantissa, "-") {
		sign = "-"
		mantissa = mantissa[1:]
	}
	if point := strings.IndexByte(mantissa, '.'); point >= 0 {
		exponent.Sub(exponent, big.NewInt(int64(len(mantissa)-point-1)))
		mantissa = mantissa[:point] + mantissa[point+1:]
	}
	mantissa = strings.TrimLeft(mantissa, "0")
	trimmed := strings.TrimRight(mantissa, "0")
	if trimmed == "" {
		return "0"
	}
	exponent.Add(exponent, big.NewInt(int64(len(mantissa)-len(trimmed))))
	return sign + trimmed + "e" + exponent.String()
}
