package agentlab_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
	"github.com/verocorp/tesser-build/internal/experimentcorpus"
)

type evidenceFile struct {
	File   string `json:"file"`
	SHA256 string `json:"sha256"`
}

type evidenceRecord struct {
	Task                int          `json:"task"`
	Family              string       `json:"family"`
	Arm                 string       `json:"arm"`
	Followup            string       `json:"followup"`
	Seed                int64        `json:"seed"`
	InitialSource       evidenceFile `json:"initial_source"`
	SubmittedSource     evidenceFile `json:"submitted_source"`
	VerifierResult      evidenceFile `json:"verifier_result"`
	AgentReport         evidenceFile `json:"agent_report"`
	ContractSHA256      string       `json:"contract_sha256"`
	SubmittedTreeSHA256 string       `json:"submitted_tree_sha256"`
	ReleasedAt          time.Time    `json:"released_at"`
	DeadlineAt          time.Time    `json:"deadline_at"`
	VerifiedObservedAt  time.Time    `json:"verified_observed_at"`
	CappedCompletionMS  int64        `json:"capped_completion_ms"`
	Status              string       `json:"status"`
	ProbeProcesses      int          `json:"probe_processes"`
}

func TestPublishedPolicyEvidenceReplays(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal("evidence replay requires python3:", err)
	}
	root := filepath.Join("evidence", "2026-09-26")
	content, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest struct {
		Records []evidenceRecord `json:"records"`
	}
	if err := json.Unmarshal(content, &manifest); err != nil || len(manifest.Records) != 4 {
		t.Fatalf("expected four published records: %v", err)
	}
	for _, record := range manifest.Records {
		t.Run(record.Family+"/"+record.Arm, func(t *testing.T) {
			files := []evidenceFile{record.InitialSource, record.SubmittedSource, record.VerifierResult, record.AgentReport}
			for _, file := range files {
				content, err := os.ReadFile(filepath.Join(root, file.File))
				if err != nil {
					t.Fatal(err)
				}
				digest := sha256.Sum256(content)
				if hex.EncodeToString(digest[:]) != file.SHA256 {
					t.Fatalf("published artifact changed: %s", file.File)
				}
			}
			candidate := filepath.Join(t.TempDir(), "candidate")
			if err := experimentcorpus.Generate(experimentcorpus.Options{
				Family: record.Family, Variant: record.Arm, Seed: record.Seed, Out: candidate,
			}); err != nil {
				t.Fatal(err)
			}
			initial, err := os.ReadFile(filepath.Join(root, record.InitialSource.File))
			if err != nil {
				t.Fatal(err)
			}
			generated, err := os.ReadFile(filepath.Join(candidate, "application.py"))
			if err != nil || !bytes.Equal(initial, generated) {
				t.Fatal("producer no longer recreates the frozen starting source")
			}
			submitted, err := os.ReadFile(filepath.Join(root, record.SubmittedSource.File))
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(candidate, "application.py"), submitted, 0644); err != nil {
				t.Fatal(err)
			}
			published, err := os.ReadFile(filepath.Join(root, record.VerifierResult.File))
			if err != nil {
				t.Fatal(err)
			}
			var previous experiment.Result
			if err := json.Unmarshal(published, &previous); err != nil {
				t.Fatal(err)
			}
			result := experiment.Verify(context.Background(), experiment.Options{
				ScenarioPath: filepath.Join("scenarios", record.Family+".json"),
				CandidateDir: candidate, Command: []string{python, "-B", "application.py"},
				Followup: record.Followup, Deadline: 15 * time.Second,
			})
			if result.Status != experiment.Correct || previous.Status != result.Status ||
				result.SourceDigest != record.SubmittedTreeSHA256 || result.SourceDigest != previous.SourceDigest ||
				result.ContractDigest != record.ContractSHA256 || result.ContractDigest != previous.ContractDigest ||
				len(result.Stages) != record.ProbeProcesses || record.Status != result.Status {
				t.Fatalf("published evidence no longer replays: %+v", result)
			}
			if record.VerifiedObservedAt.After(record.DeadlineAt) || record.VerifiedObservedAt.Before(record.ReleasedAt) ||
				record.CappedCompletionMS != record.VerifiedObservedAt.Sub(record.ReleasedAt).Milliseconds() {
				t.Fatalf("published timing is internally inconsistent: %+v", record)
			}
		})
	}
}
