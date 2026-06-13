package genexclude_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"golang.org/x/tools/go/packages"
	"gopkg.in/yaml.v3"

	"github.com/chrisconley/go-ddd/internal/genexclude"
	"github.com/chrisconley/go-ddd/internal/voscan"
)

func loadDom(t *testing.T) []*packages.Package {
	t.Helper()
	gopath, err := filepath.Abs("testdata")
	if err != nil {
		t.Fatal(err)
	}
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedTypes | packages.NeedSyntax |
			packages.NeedTypesInfo | packages.NeedDeps | packages.NeedImports,
		Env: append(os.Environ(), "GOPATH="+gopath, "GO111MODULE=off", "GOFLAGS="),
	}
	pkgs, err := packages.Load(cfg, "dom")
	if err != nil {
		t.Fatal(err)
	}
	if packages.PrintErrors(pkgs) > 0 {
		t.Fatal("package load errors")
	}
	return pkgs
}

func TestClassify(t *testing.T) {
	entries := genexclude.Classify(loadDom(t))

	got := map[string]string{}
	for _, e := range entries {
		got[e.Name] = e.Reason
	}

	// Entities/aggregates are classified with the strongest matching signal.
	wantReasonContains := map[string]string{
		"Ledger":   "has ID() method",
		"Account":  "field: id string",
		"Transfer": "mutated by (*Transfer).Apply()",
		"Basket":   "holds child collection items []Item",
	}
	for name, want := range wantReasonContains {
		reason, ok := got[name]
		if !ok {
			t.Errorf("expected %s to be excluded, but it was not", name)
			continue
		}
		if !strings.Contains(reason, want) {
			t.Errorf("%s reason = %q, want it to contain %q", name, reason, want)
		}
	}

	// Pure value objects must NOT be excluded.
	for _, name := range []string{"Money", "Item"} {
		if _, ok := got[name]; ok {
			t.Errorf("value object %s must not be excluded, got reason %q", name, got[name])
		}
	}

	if len(entries) != len(wantReasonContains) {
		t.Errorf("got %d entries, want %d: %v", len(entries), len(wantReasonContains), got)
	}
}

func TestRenderRoundTrip(t *testing.T) {
	entries := genexclude.Classify(loadDom(t))
	out := genexclude.Render(entries, "2026-06-13")

	var cfg voscan.Config
	if err := yaml.Unmarshal([]byte(out), &cfg); err != nil {
		t.Fatalf("generated YAML does not parse: %v\n%s", err, out)
	}
	set := map[string]bool{}
	for _, name := range cfg.Exclude {
		set[name] = true
	}
	for _, name := range []string{"Ledger", "Account", "Transfer", "Basket"} {
		if !set[name] {
			t.Errorf("round-tripped exclude set missing %s\nYAML:\n%s", name, out)
		}
	}
	if set["Money"] || set["Item"] {
		t.Errorf("round-tripped exclude set wrongly contains a value object\nYAML:\n%s", out)
	}
}

func TestRenderEmpty(t *testing.T) {
	out := genexclude.Render(nil, "2026-06-13")
	var cfg voscan.Config
	if err := yaml.Unmarshal([]byte(out), &cfg); err != nil {
		t.Fatalf("empty YAML does not parse: %v\n%s", err, out)
	}
	if len(cfg.Exclude) != 0 {
		t.Errorf("empty render should yield no excludes, got %v", cfg.Exclude)
	}
}
