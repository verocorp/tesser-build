package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"testing"

	"github.com/verocorp/tesser-build/internal/experiment"
)

func TestCLITrialEndToEnd(t *testing.T) {
	scenario, candidate, path := cliPaths(t)
	var output bytes.Buffer
	args := []string{"trial", "--scenario", scenario, "--candidate", candidate, "--agent-json", `["/bin/true"]`, "--command-json", `["/bin/cat"]`, "--result", path, "--deadline", "1s", "--arm", "fixture"}
	if code := run(context.Background(), args, &output, &output); code != 0 {
		t.Fatalf("trial CLI failed: %s", output.String())
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var result experiment.TrialResult
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatal(err)
	}
	if result.Status != experiment.Correct || result.Agent == nil || result.Verification == nil || result.VerifiedAt == nil || result.MeasurementScope != "local_agent_process_through_verification" {
		t.Fatalf("trial CLI did not record end-to-end execution: %s", data)
	}
	args = append(args, "--agent-json", `["/bin/sh","-c","exit 8"]`)
	if code := run(context.Background(), args, &output, &output); code == 0 {
		t.Fatal("failed agent produced successful CLI exit")
	}
}
