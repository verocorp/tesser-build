package primitiveaccessor_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/chrisconley/go-ddd/passes/primitiveaccessor"
)

func TestPrimitiveAccessor(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), primitiveaccessor.Analyzer, "a")
}

func TestPrimitiveAccessor_Exclude(t *testing.T) {
	if err := primitiveaccessor.Analyzer.Flags.Set("exclude", "Entity"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = primitiveaccessor.Analyzer.Flags.Set("exclude", "") }()
	analysistest.Run(t, analysistest.TestData(), primitiveaccessor.Analyzer, "excl")
}
