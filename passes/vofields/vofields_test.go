package vofields_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/verocorp/go-ddd/passes/vofields"
)

func TestVOFields(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), vofields.Analyzer, "a")
}

func TestVOFields_Exclude(t *testing.T) {
	if err := vofields.Analyzer.Flags.Set("exclude", "Ledger"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = vofields.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), vofields.Analyzer, "excl")
}
