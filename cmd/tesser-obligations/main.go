package main

import (
	"encoding/json"
	"io"
	"os"

	"github.com/verocorp/tesser-build/internal/obligationeval"
)

func main() {
	if len(os.Args) != 1 {
		writeError("input_error", "usage: tesser-obligations < envelope.json > report.json")
		os.Exit(2)
	}
	input, err := io.ReadAll(os.Stdin)
	if err != nil {
		writeError("input_error", err.Error())
		os.Exit(2)
	}
	report, err := obligationeval.Evaluate(input)
	if err != nil {
		writeError("input_error", err.Error())
		os.Exit(2)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(report); err != nil {
		writeError("output_error", err.Error())
		os.Exit(1)
	}
}

func writeError(status, message string) {
	_ = json.NewEncoder(os.Stderr).Encode(struct {
		SchemaVersion string `json:"schema_version"`
		Status        string `json:"status"`
		Error         string `json:"error"`
	}{obligationeval.SchemaVersion, status, message})
}
