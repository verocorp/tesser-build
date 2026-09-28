package obligationeval_test

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/verocorp/tesser-build/internal/obligationeval"
)

func TestFrozenPilotInputs(t *testing.T) {
	data, err := os.ReadFile("pilot/LIVE-FROZEN.json")
	if err != nil {
		t.Fatal(err)
	}
	var frozen struct {
		Hashes map[string]string `json:"sha256"`
	}
	if err := json.Unmarshal(data, &frozen); err != nil {
		t.Fatal(err)
	}
	if len(frozen.Hashes) != 10 {
		t.Fatalf("expected ten frozen input artifacts, got %d", len(frozen.Hashes))
	}
	for name, wanted := range frozen.Hashes {
		if !filepath.IsLocal(name) {
			t.Fatalf("nonlocal frozen path %q", name)
		}
		content, err := os.ReadFile(filepath.Join("pilot", name))
		if err != nil {
			t.Fatal(err)
		}
		digest := sha256.Sum256(content)
		if hex.EncodeToString(digest[:]) != wanted {
			t.Errorf("frozen artifact changed: %s", name)
		}
	}
	data, err = os.ReadFile("pilot/live/responses.json")
	if err != nil {
		t.Fatal(err)
	}
	var responses []struct {
		CaseID string `json:"case_id"`
		Raw    string `json:"candidate_raw"`
		Hash   string `json:"candidate_sha256"`
	}
	if err := json.Unmarshal(data, &responses); err != nil {
		t.Fatal(err)
	}
	data, err = os.ReadFile("pilot/live/replay-a.json")
	if err != nil {
		t.Fatal(err)
	}
	var envelope obligationeval.Envelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		t.Fatal(err)
	}
	if len(responses) != 10 || len(envelope.Records) != 10 {
		t.Fatal("pilot must retain ten first outputs and replay records")
	}
	seen := map[string]bool{}
	for i, response := range responses {
		digest := sha256.Sum256([]byte(response.Raw))
		if seen[response.CaseID] || hex.EncodeToString(digest[:]) != response.Hash || envelope.Records[i].Case.CaseID != response.CaseID || envelope.Records[i].CandidateRaw != response.Raw {
			t.Errorf("first output changed or misbound: %s", response.CaseID)
		}
		seen[response.CaseID] = true
	}
}

func TestPilotEvidence(t *testing.T) {
	for _, reviewer := range []string{"a", "b"} {
		t.Run(reviewer, func(t *testing.T) {
			data, err := os.ReadFile("pilot/live/replay-a.json")
			if err != nil {
				t.Fatal(err)
			}
			var envelope obligationeval.Envelope
			if err := json.Unmarshal(data, &envelope); err != nil {
				t.Fatal(err)
			}
			data, err = os.ReadFile("pilot/live/reviewer-" + reviewer + "/judgments.json")
			if err != nil {
				t.Fatal(err)
			}
			var reviews []json.RawMessage
			if err := json.Unmarshal(data, &reviews); err != nil {
				t.Fatal(err)
			}
			if len(envelope.Records) != 10 || len(reviews) != 10 {
				t.Fatal("pilot must retain ten independent reviews")
			}
			for i := range envelope.Records {
				envelope.Records[i].Review = reviews[i]
			}
			data, err = json.Marshal(envelope)
			if err != nil {
				t.Fatal(err)
			}
			report, err := obligationeval.Evaluate(data)
			if err != nil {
				t.Fatal(err)
			}
			results := make([]map[string]any, 0, len(report.Results))
			for _, result := range report.Results {
				results = append(results, map[string]any{
					"case_id": result.Input.Case.CaseID, "candidate_label": result.Input.CandidateLabel,
					"status": result.Status, "pass": result.Pass, "reasons": result.Reasons,
					"candidate_format_valid": result.CandidateFormatValid,
					"grounding":              result.Grounding, "metrics": result.Metrics,
				})
			}
			data, err = json.Marshal(map[string]any{
				"schema_version": report.SchemaVersion, "results": results,
				"by_candidate": report.ByCandidate, "by_split": report.BySplit,
				"by_candidate_split": report.ByCandidateSplit,
			})
			if err != nil {
				t.Fatal(err)
			}
			var actual, wanted any
			if err := json.Unmarshal(data, &actual); err != nil {
				t.Fatal(err)
			}
			data, err = os.ReadFile("pilot/live/report-" + reviewer + ".json")
			if err != nil {
				t.Fatal(err)
			}
			if err := json.Unmarshal(data, &wanted); err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(actual, wanted) {
				t.Fatal("frozen pilot diagnostic changed; inspect the raw review and arithmetic")
			}
		})
	}
}
