package voconstructor_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/chrisconley/go-ddd/passes/voconstructor"
)

func TestVOConstructor(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), voconstructor.Analyzer, "a")
}

func TestVOConstructor_Exclude(t *testing.T) {
	if err := voconstructor.Analyzer.Flags.Set("exclude", "Ledger"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = voconstructor.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), voconstructor.Analyzer, "excl")
}
