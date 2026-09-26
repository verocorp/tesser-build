package experiment_test

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
)

func TestTrialAgentEditsBeforeVerifiedSnapshot(t *testing.T) {
	options := optionsFor(t, "exit 4")
	result := experiment.RunTrial(context.Background(), experiment.TrialOptions{
		Verification: options, Arm: "fixture",
		Agent: []string{"/bin/sh", "-c", "cat > received-brief.json; sleep 0.02; printf 'cat\\n' > main.sh"},
	})
	if result.Status != experiment.Correct || !result.Eligible || result.Agent == nil || result.Verification == nil || result.VerifiedAt == nil || result.CappedCompletionMS == nil {
		t.Fatalf("trial did not verify agent edits: %+v", result)
	}
	if result.Agent.Kind != "agent" || result.Agent.StartedAt.Before(result.TaskReleasedAt) || result.Verification.VerificationStartedAt.Before(result.Agent.EndedAt) || result.VerifiedAt.Before(result.Verification.VerificationEndedAt) {
		t.Fatalf("trial spans out of order: %+v", result)
	}
	if *result.CappedCompletionMS != result.VerifiedAt.Sub(result.TaskReleasedAt).Milliseconds() || *result.CappedCompletionMS >= result.TaskBudgetMS || result.Verification.VerificationBudgetMS >= result.TaskBudgetMS {
		t.Fatalf("trial did not use one deadline: %+v", result)
	}
	if result.InitialSourceDigest == result.Verification.SourceDigest || len(result.ConfigurationDigest) != 64 || result.ContractDigest != result.Verification.ContractDigest {
		t.Fatalf("trial digests incorrect: %+v", result)
	}
	if result.Usage != "unknown" || result.Cost != "unknown" || result.HumanIntervention.Status != "unknown" || result.HumanIntervention.Events != nil {
		t.Fatalf("unmeasured metrics claimed: %+v", result)
	}
	brief, err := os.ReadFile(filepath.Join(options.CandidateDir, "received-brief.json"))
	if err != nil {
		t.Fatal(err)
	}
	for _, hidden := range []string{"secret-change", "private-answer", "base_expected", `"probes"`} {
		if strings.Contains(string(brief), hidden) {
			t.Fatalf("agent received hidden oracle %q", hidden)
		}
	}
}

func TestTrialRetainsFailuresWithWholeBudgetCap(t *testing.T) {
	cases := []struct {
		name         string
		agent        []string
		candidate    string
		status       string
		verification bool
	}{
		{"agent-failure", []string{"/bin/sh", "-c", "echo failed >&2; exit 7"}, "cat", experiment.Incorrect, false},
		{"agent-timeout-before-verification", []string{"/bin/sh", "-c", "sleep 2"}, "cat", experiment.Timeout, false},
		{"agent-success-wrong-behavior", []string{"/bin/true"}, `printf '{}\n{}\n'`, experiment.Incorrect, true},
		{"agent-success-verifier-timeout", []string{"/bin/true"}, "sleep 2; cat", experiment.Timeout, true},
		{"missing-agent", []string{"/not-a-real-agent"}, "cat", experiment.InfraError, false},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			options := optionsFor(t, test.candidate)
			options.Deadline = 150 * time.Millisecond
			result := experiment.RunTrial(context.Background(), experiment.TrialOptions{Verification: options, Agent: test.agent, Arm: "fixture"})
			if result.Status != test.status || !result.Eligible || result.CappedCompletionMS == nil || *result.CappedCompletionMS != 150 || result.VerifiedAt != nil || (result.Verification != nil) != test.verification {
				t.Fatalf("failed trial lost or mismeasured: %+v", result)
			}
			if result.Agent == nil || result.TaskEndedAt.Before(result.Agent.EndedAt) {
				t.Fatalf("agent span missing: %+v", result)
			}
		})
	}
}

func TestTrialReportsOnlySuppliedInterventionEvidence(t *testing.T) {
	options := optionsFor(t, "cat")
	path := filepath.Join(t.TempDir(), "events.json")
	events := []experiment.InterventionEvent{{At: time.Now().UTC(), Kind: "human_instruction", Description: "Caller supplied setup instruction."}}
	data, err := json.Marshal(events)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0600); err != nil {
		t.Fatal(err)
	}
	result := experiment.RunTrial(context.Background(), experiment.TrialOptions{Verification: options, Agent: []string{"/bin/true"}, Arm: "fixture", InterventionsPath: path})
	if result.Status != experiment.Correct || result.HumanIntervention.Status != "reported" || len(result.HumanIntervention.Events) != 1 || result.HumanIntervention.Events[0] != events[0] {
		t.Fatalf("real supplied event not retained: %+v", result)
	}
	if err := os.WriteFile(path, []byte(`[{}]`), 0600); err != nil {
		t.Fatal(err)
	}
	result = experiment.RunTrial(context.Background(), experiment.TrialOptions{Verification: options, Agent: []string{"/bin/true"}, Arm: "fixture", InterventionsPath: path})
	if result.Status != experiment.InfraError || result.HumanIntervention.Status != "unknown" || result.HumanIntervention.Error == "" {
		t.Fatalf("malformed intervention evidence accepted: %+v", result)
	}
}

func TestTrialInvalidContractNeverStartsAgent(t *testing.T) {
	options := optionsFor(t, "cat")
	options.ScenarioPath += ".missing"
	result := experiment.RunTrial(context.Background(), experiment.TrialOptions{Verification: options, Agent: []string{"/bin/true"}, Arm: "fixture"})
	if result.Status != experiment.InfraError || result.Eligible || result.Agent != nil || result.Verification != nil || result.CappedCompletionMS != nil {
		t.Fatalf("invalid trial was released to agent: %+v", result)
	}
}

func TestTrialRejectsAgentOracleMutation(t *testing.T) {
	options := optionsFor(t, "cat")
	result := experiment.RunTrial(context.Background(), experiment.TrialOptions{
		Verification: options, Arm: "fixture", Agent: []string{"/bin/sh", "-c", `printf '{}' > "$1"`, "fixture", options.ScenarioPath},
	})
	if result.Status != experiment.InfraError || result.Verification != nil || !strings.Contains(result.Error, "oracle changed") || result.CappedCompletionMS == nil {
		t.Fatalf("oracle mutation accepted: %+v", result)
	}
}
