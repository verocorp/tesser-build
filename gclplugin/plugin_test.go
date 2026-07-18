package gclplugin

import (
	"testing"

	"github.com/golangci/plugin-module-register/register"

	"github.com/verocorp/tesser-build/internal/analyzers"
)

// TestBuildAnalyzers_MatchesRegistry locks the plugin to the single analyzer
// registry, so the golangci-lint binary and the standalone tessercheck can never
// expose different analyzer sets.
func TestBuildAnalyzers_MatchesRegistry(t *testing.T) {
	p, err := New(nil)
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	got, err := p.BuildAnalyzers()
	if err != nil {
		t.Fatalf("BuildAnalyzers: %v", err)
	}
	if len(got) != len(analyzers.All) {
		t.Fatalf("plugin exposes %d analyzers, registry has %d", len(got), len(analyzers.All))
	}
	for i, a := range got {
		if a != analyzers.All[i] {
			t.Errorf("analyzer %d: plugin has %q, registry has %q", i, a.Name, analyzers.All[i].Name)
		}
	}
}

// TestGetLoadMode_TypesInfo guards the correctness precondition: most tessercheck
// analyzers are type-aware, so syntax-only would silently break them.
func TestGetLoadMode_TypesInfo(t *testing.T) {
	p, _ := New(nil)
	if got := p.GetLoadMode(); got != register.LoadModeTypesInfo {
		t.Fatalf("load mode = %q, want %q", got, register.LoadModeTypesInfo)
	}
}
