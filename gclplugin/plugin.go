// Package gclplugin registers tessercheck's analyzers as a golangci-lint module
// plugin, so a custom-built golangci-lint binary surfaces the DDD value-object
// diagnostics inline — native go.lintOnSave squiggles in the editor, alongside a
// consumer's other linters, with no third-party "run task on save" extension.
//
// Build a custom golangci-lint with `golangci-lint custom` against a
// .custom-gcl.yml that imports this package, then enable the "tessercheck" linter in
// .golangci.yml. See examples/golangci/ and the README "Editor integration".
//
// Config travels unchanged: the analyzers read .tesser-build.yaml from the package
// directory regardless of driver, so excludes are NOT duplicated into
// .golangci.yml. The per-analyzer -exclude flags are inert here (golangci-lint
// does not pass analyzer flags); .tesser-build.yaml stays the single config source.
package gclplugin

import (
	"github.com/golangci/plugin-module-register/register"
	"golang.org/x/tools/go/analysis"

	"github.com/verocorp/tesser-build/internal/analyzers"
)

func init() {
	register.Plugin("tessercheck", New)
}

// New is the golangci-lint plugin constructor. tessercheck takes its configuration
// from .tesser-build.yaml, not from golangci-lint settings, so settings is ignored.
func New(settings any) (register.LinterPlugin, error) {
	return &plugin{}, nil
}

type plugin struct{}

// BuildAnalyzers returns every tessercheck analyzer — the same
// internal/analyzers.All registry cmd/tessercheck composes — so the plugin and the
// standalone binary can never drift.
func (p *plugin) BuildAnalyzers() ([]*analysis.Analyzer, error) {
	return analyzers.All, nil
}

// GetLoadMode requests type information: most tessercheck analyzers are type-aware
// (struct fields, method sets, comparability), so syntax-only is insufficient.
func (p *plugin) GetLoadMode() string {
	return register.LoadModeTypesInfo
}
