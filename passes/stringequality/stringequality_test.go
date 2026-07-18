package stringequality_test

import (
	"testing"

	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/verocorp/tesser-build/passes/stringequality"
)

func TestStringEquality(t *testing.T) {
	analysistest.Run(t, analysistest.TestData(), stringequality.Analyzer, "a", "ext")
}
