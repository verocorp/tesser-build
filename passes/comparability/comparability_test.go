package comparability_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/verocorp/tesser-build/passes/comparability"
)

func TestComparability(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), comparability.Analyzer, "a")
}

func TestComparability_Exclude(t *testing.T) {
	if err := comparability.Analyzer.Flags.Set("exclude", "Aggregate"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = comparability.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), comparability.Analyzer, "excl")
}
