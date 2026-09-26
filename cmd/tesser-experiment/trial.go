package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
)

func runTrial(ctx context.Context, args []string, stderr io.Writer) int {
	flags := flag.NewFlagSet("trial", flag.ContinueOnError)
	flags.SetOutput(stderr)
	scenario := flags.String("scenario", "", "external scenario oracle")
	candidate := flags.String("candidate", "", "prepared candidate directory the agent may edit")
	agentJSON := flags.String("agent-json", "", "agent argv; receives brief JSON on stdin")
	commandJSON := flags.String("command-json", "", "candidate verification argv")
	gatesJSON := flags.String("gate-json", "[]", "JSON array of gate argv arrays")
	resultPath := flags.String("result", "", "trial result outside the candidate")
	deadline := flags.String("deadline", "", "whole-task duration including agent and verification")
	followup := flags.String("followup", "", "selected followup")
	arm := flags.String("arm", "", "caller-assigned experimental arm identifier")
	interventions := flags.String("interventions", "", "caller-reported timestamped intervention JSON events, read after the run")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() != 0 || *scenario == "" || *candidate == "" || *resultPath == "" || *arm == "" {
		fmt.Fprintln(stderr, "trial requires --scenario, --candidate, --agent-json, --command-json, --result, --deadline, and --arm")
		return 2
	}
	budget, err := time.ParseDuration(*deadline)
	if err != nil || budget < time.Millisecond {
		fmt.Fprintln(stderr, "trial deadline must be a duration of at least 1ms")
		return 2
	}
	agent, err := parseArgv([]byte(*agentJSON))
	if err != nil {
		fmt.Fprintln(stderr, "invalid agent-json:", err)
		return 2
	}
	command, err := parseArgv([]byte(*commandJSON))
	if err != nil {
		fmt.Fprintln(stderr, "invalid command-json:", err)
		return 2
	}
	var rawGates []json.RawMessage
	if err := json.Unmarshal([]byte(*gatesJSON), &rawGates); err != nil || rawGates == nil {
		fmt.Fprintln(stderr, "gate-json must be a JSON array of argv arrays")
		return 2
	}
	gates := make([][]string, 0, len(rawGates))
	for _, raw := range rawGates {
		gate, err := parseArgv(raw)
		if err != nil {
			fmt.Fprintln(stderr, "invalid gate:", err)
			return 2
		}
		gates = append(gates, gate)
	}
	path, err := safeResultPath(*resultPath, *candidate, *scenario)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	result := experiment.RunTrial(ctx, experiment.TrialOptions{
		Verification: experiment.Options{ScenarioPath: *scenario, CandidateDir: *candidate, Command: command, Gates: gates, Deadline: budget, Followup: *followup},
		Agent:        agent, Arm: *arm, InterventionsPath: *interventions,
	})
	if err := writeResult(path, result); err != nil {
		fmt.Fprintln(stderr, "write trial result:", err)
		return 1
	}
	if result.Status != experiment.Correct {
		fmt.Fprintf(stderr, "%s: %s\n", result.Status, result.Error)
		return 1
	}
	return 0
}
