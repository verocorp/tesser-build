package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/verocorp/tesser-build/internal/obligationeval"
)

func TestCLIExecutable(t *testing.T) {
	binary := filepath.Join(t.TempDir(), "tesser-obligations")
	if output, err := exec.Command("go", "build", "-o", binary, ".").CombinedOutput(); err != nil {
		t.Fatalf("build: %v\n%s", err, output)
	}
	var source obligationeval.Case
	var gold obligationeval.Gold
	var judgments []json.RawMessage
	for _, fixture := range []struct {
		name   string
		target interface{}
	}{
		{"case", &source}, {"gold", &gold}, {"judgments", &judgments},
	} {
		data, err := os.ReadFile("../../internal/obligationeval/testdata/" + fixture.name + ".json")
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(data, fixture.target); err != nil {
			t.Fatal(err)
		}
	}
	record := obligationeval.Record{CandidateLabel: "calibration_01", Case: source, Gold: gold, CandidateRaw: `{"case_id":"D01","items":[]}`, Review: judgments[0]}
	for _, test := range []struct {
		name, raw, status string
		review            json.RawMessage
	}{
		{"scored_failure", record.CandidateRaw, "scored", record.Review},
		{"malformed_candidate", "not JSON", "candidate_failure", record.Review},
		{"unreviewed", record.CandidateRaw, "unscorable", json.RawMessage(`null`)},
	} {
		t.Run(test.name, func(t *testing.T) {
			input := record
			input.CandidateRaw = test.raw
			input.Review = test.review
			data, err := json.Marshal(obligationeval.Envelope{SchemaVersion: obligationeval.SchemaVersion, Records: []obligationeval.Record{input}})
			if err != nil {
				t.Fatal(err)
			}
			command := exec.Command(binary)
			command.Stdin = bytes.NewReader(data)
			var stderr bytes.Buffer
			command.Stderr = &stderr
			output, err := command.Output()
			if err != nil || stderr.Len() != 0 {
				t.Fatalf("exit: %v, stderr: %s", err, stderr.String())
			}
			var report obligationeval.Report
			if err := json.Unmarshal(output, &report); err != nil {
				t.Fatal(err)
			}
			if report.SchemaVersion != obligationeval.SchemaVersion || len(report.Results) != 1 || report.Results[0].Status != test.status || report.Results[0].Input.CandidateRaw != test.raw {
				t.Fatalf("%s", output)
			}
			if test.status == "scored" && (report.Results[0].Pass == nil || *report.Results[0].Pass) {
				t.Fatal("empty control should be scored and fail")
			}
		})
	}
	for _, test := range []struct {
		name, input string
		args        []string
	}{
		{"invalid_json", "not JSON", nil}, {"invalid_envelope", `{}`, nil}, {"unexpected_arguments", "", []string{"unexpected"}},
	} {
		t.Run(test.name, func(t *testing.T) {
			command := exec.Command(binary, test.args...)
			command.Stdin = bytes.NewBufferString(test.input)
			var stdout, stderr bytes.Buffer
			command.Stdout = &stdout
			command.Stderr = &stderr
			err := command.Run()
			if err == nil || command.ProcessState.ExitCode() != 2 || stdout.Len() != 0 || stderr.Len() == 0 {
				t.Fatalf("error=%v stdout=%s stderr=%s", err, stdout.String(), stderr.String())
			}
			var failure struct {
				SchemaVersion string `json:"schema_version"`
				Status        string `json:"status"`
				Error         string `json:"error"`
			}
			if err := json.Unmarshal(stderr.Bytes(), &failure); err != nil {
				t.Fatal(err)
			}
			if failure.SchemaVersion != obligationeval.SchemaVersion || failure.Status != "input_error" || failure.Error == "" {
				t.Fatalf("%s", stderr.String())
			}
		})
	}
}
