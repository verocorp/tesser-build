package mustnew_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/verocorp/tesser-build/passes/mustnew"
)

func TestMustNew(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), mustnew.Analyzer, "a")
}

func TestMustNew_Exclude(t *testing.T) {
	if err := mustnew.Analyzer.Flags.Set("exclude", "Ledger"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = mustnew.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), mustnew.Analyzer, "excl")
}
