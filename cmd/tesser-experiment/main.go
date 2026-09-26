package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	os.Exit(run(ctx, os.Args[1:], os.Stdout, os.Stderr))
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	if len(args) > 0 && args[0] == "trial" {
		return runTrial(ctx, args[1:], stderr)
	}
	if len(args) == 0 || (args[0] != "verify" && args[0] != "brief") {
		fmt.Fprintln(stderr, "usage: tesser-experiment verify --scenario <json> --candidate <dir> --command-json <JSON argv> --result <json> --deadline <duration> [--followup id] [--gate-json <JSON array of argv arrays>]")
		fmt.Fprintln(stderr, "       tesser-experiment brief --scenario <json> [--followup id]")
		fmt.Fprintln(stderr, "       tesser-experiment trial --scenario <json> --candidate <dir> --agent-json <JSON argv> --command-json <JSON argv> --result <json> --deadline <duration> --arm <id> [--followup id] [--gate-json <JSON array of argv arrays>] [--interventions <json>]")
		fmt.Fprintln(stderr, experiment.SafetyNotice)
		return 2
	}
	flags := flag.NewFlagSet(args[0], flag.ContinueOnError)
	flags.SetOutput(stderr)
	scenarioPath := flags.String("scenario", "", "scenario JSON file outside the candidate tree")
	followup := flags.String("followup", "", "selected followup id")
	var candidate, commandJSON, gatesJSON, resultPath, deadline string
	if args[0] == "verify" {
		flags.StringVar(&candidate, "candidate", "", "candidate directory to copy")
		flags.StringVar(&commandJSON, "command-json", "", "JSON argv array; no implicit shell")
		flags.StringVar(&gatesJSON, "gate-json", "[]", "JSON array of gate argv arrays")
		flags.StringVar(&resultPath, "result", "", "result JSON outside the candidate tree")
		flags.StringVar(&deadline, "deadline", "", "positive overall verification budget, such as 30s")
	}
	if err := flags.Parse(args[1:]); err != nil {
		return 2
	}
	if flags.NArg() != 0 || *scenarioPath == "" {
		fmt.Fprintln(stderr, "a scenario path is required; positional arguments are not accepted")
		return 2
	}
	if args[0] == "brief" {
		scenario, err := experiment.LoadScenario(*scenarioPath)
		if err != nil {
			fmt.Fprintln(stderr, err)
			return 1
		}
		brief, err := scenario.Brief(*followup)
		if err != nil {
			fmt.Fprintln(stderr, err)
			return 1
		}
		if err := json.NewEncoder(stdout).Encode(brief); err != nil {
			fmt.Fprintln(stderr, err)
			return 1
		}
		return 0
	}
	if candidate == "" || resultPath == "" || commandJSON == "" || deadline == "" {
		fmt.Fprintln(stderr, "verify requires --candidate, --command-json, --result, and --deadline")
		return 2
	}
	budget, err := time.ParseDuration(deadline)
	if err != nil || budget <= 0 {
		fmt.Fprintln(stderr, "deadline must be a valid positive duration")
		return 2
	}
	command, err := parseArgv([]byte(commandJSON))
	if err != nil {
		fmt.Fprintln(stderr, "command-json must be a nonempty JSON array of strings")
		return 2
	}
	var rawGates []json.RawMessage
	if err := json.Unmarshal([]byte(gatesJSON), &rawGates); err != nil || rawGates == nil {
		fmt.Fprintln(stderr, "gate-json must be a JSON array of argv arrays")
		return 2
	}
	gates := make([][]string, 0, len(rawGates))
	for _, raw := range rawGates {
		gate, err := parseArgv(raw)
		if err != nil {
			fmt.Fprintln(stderr, "each gate must be a nonempty JSON array of strings")
			return 2
		}
		gates = append(gates, gate)
	}
	resolvedResult, err := safeResultPath(resultPath, candidate, *scenarioPath)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	result := experiment.Verify(ctx, experiment.Options{
		ScenarioPath: *scenarioPath, CandidateDir: candidate, Command: command,
		Gates: gates, Deadline: budget, Followup: *followup,
	})
	if err := writeResult(resolvedResult, result); err != nil {
		fmt.Fprintln(stderr, "write result:", err)
		return 1
	}
	if result.Status != experiment.Correct {
		fmt.Fprintf(stderr, "%s: %s\n", result.Status, result.Error)
		return 1
	}
	return 0
}

func parseArgv(data []byte) ([]string, error) {
	var values []any
	if err := json.Unmarshal(data, &values); err != nil {
		return nil, err
	}
	if len(values) == 0 {
		return nil, fmt.Errorf("argv cannot be empty")
	}
	argv := make([]string, len(values))
	for index, value := range values {
		text, ok := value.(string)
		if !ok {
			return nil, fmt.Errorf("argv entries must be strings")
		}
		argv[index] = text
	}
	return argv, nil
}

func safeResultPath(path, candidate, scenario string) (string, error) {
	parent, err := filepath.EvalSymlinks(filepath.Dir(path))
	if err != nil {
		return "", fmt.Errorf("result directory: %w", err)
	}
	resolved, err := filepath.Abs(filepath.Join(parent, filepath.Base(path)))
	if err != nil {
		return "", err
	}
	source, err := filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	if canonical, err := filepath.EvalSymlinks(source); err == nil {
		source = canonical
	}
	if experiment.ContainsPath(source, resolved) {
		return "", fmt.Errorf("result must be outside the candidate tree")
	}
	oracle, err := filepath.Abs(scenario)
	if err != nil {
		return "", err
	}
	if canonical, err := filepath.EvalSymlinks(oracle); err == nil {
		oracle = canonical
	}
	if resolved == oracle {
		return "", fmt.Errorf("result must not overwrite the scenario")
	}
	return resolved, nil
}

func writeResult(path string, result any) error {
	file, err := os.CreateTemp(filepath.Dir(path), ".tesser-experiment-result-*")
	if err != nil {
		return err
	}
	defer os.Remove(file.Name())
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	encodeErr := encoder.Encode(result)
	closeErr := file.Close()
	if encodeErr != nil {
		return encodeErr
	}
	if closeErr != nil {
		return closeErr
	}
	return os.Rename(file.Name(), path)
}
