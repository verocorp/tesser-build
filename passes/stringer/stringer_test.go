package stringer_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/chrisconley/go-ddd/passes/stringer"
)

func TestStringer(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), stringer.Analyzer, "a")
}

func TestStringer_Exclude(t *testing.T) {
	if err := stringer.Analyzer.Flags.Set("exclude", "Entity"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = stringer.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), stringer.Analyzer, "excl")
}
