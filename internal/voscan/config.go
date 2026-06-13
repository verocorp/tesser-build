package voscan

import (
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
// the standalone tests). A missing or unparseable file is treated as no
// excludes — the analyzers must never fail because of config.
func CombinedExcludes(pass *analysis.Pass, flagValue string) map[string]bool {
	out := ParseExcludes(flagValue)
	dir := passDir(pass)
	if dir == "" {
		return out
	}
	path, ok := FindConfig(dir)
	if !ok {
		return out
	}
	cfg, err := LoadConfig(path)
	if err != nil {
		return out
	}
	for _, name := range cfg.Exclude {
		if name = strings.TrimSpace(name); name != "" {
			out[name] = true
		}
	}
	return out
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
