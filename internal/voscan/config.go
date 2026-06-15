package voscan

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/tools/go/analysis"
	"gopkg.in/yaml.v3"
)

// ConfigName is the shared, repo-root configuration file every analyzer reads.
const ConfigName = ".go-ddd.yaml"

// Config is the .go-ddd.yaml shape: one exclude list, shared by all analyzers,
// naming the aggregate/entity types that match the value-object heuristic but
// are not value objects. Generate a starter with `ddd-vet -gen-excludes`.
type Config struct {
	Exclude []string `yaml:"exclude"`
}

// FindConfig walks up from startDir looking for .go-ddd.yaml, stopping at the
// filesystem root. It returns the path and whether one was found.
func FindConfig(startDir string) (string, bool) {
	dir := startDir
	for {
		p := filepath.Join(dir, ConfigName)
		if _, err := os.Stat(p); err == nil {
			return p, true
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", false
		}
		dir = parent
	}
}

// LoadConfig reads and parses a .go-ddd.yaml file.
func LoadConfig(path string) (*Config, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Config
	if err := yaml.Unmarshal(b, &c); err != nil {
		return nil, err
	}
	return &c, nil
}

// CombinedExcludes is the exclude set every analyzer uses: the per-analyzer
// -exclude flag value unioned with the exclude: list from the nearest
// .go-ddd.yaml above the package's directory. The file is the shared,
// version-controlled source; the flag is an override (and the only path used by
// the standalone tests).
//
// A MISSING file is not an error (no excludes from the file). A present-but-
// MALFORMED file IS an error: the analyzer returns it from Run so the tool fails
// loud. Silently treating a malformed config as "no excludes" would silently
// change enforcement in CI (a real entity suddenly flagged, or a stale belief
// that excludes apply) — the exact silent gap this toolkit exists to prevent.
func CombinedExcludes(pass *analysis.Pass, flagValue string) (map[string]bool, error) {
	out := ParseExcludes(flagValue)
	dir := passDir(pass)
	if dir == "" {
		return out, nil
	}
	fileExcludes, err := excludesFromConfig(dir)
	if err != nil {
		return nil, err
	}
	for name := range fileExcludes {
		out[name] = true
	}
	return out, nil
}

// excludesFromConfig loads the exclude set from the nearest .go-ddd.yaml above
// dir. A missing file yields an empty set and no error; a present-but-malformed
// file yields an error. Split out from CombinedExcludes so the missing-vs-
// malformed distinction is unit-testable without constructing an analysis.Pass.
func excludesFromConfig(dir string) (map[string]bool, error) {
	out := map[string]bool{}
	path, ok := FindConfig(dir)
	if !ok {
		return out, nil
	}
	cfg, err := LoadConfig(path)
	if err != nil {
		return nil, fmt.Errorf("malformed %s at %s: %w", ConfigName, path, err)
	}
	for _, name := range cfg.Exclude {
		if name = strings.TrimSpace(name); name != "" {
			out[name] = true
		}
	}
	return out, nil
}

// passDir returns the directory of the first file in the pass, the anchor for
// the .go-ddd.yaml search.
func passDir(pass *analysis.Pass) string {
	if len(pass.Files) == 0 {
		return ""
	}
	f := pass.Fset.File(pass.Files[0].Pos())
	if f == nil {
		return ""
	}
	return filepath.Dir(f.Name())
}
