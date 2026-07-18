package voscan

import (
	"os"
	"path/filepath"
	"testing"
)

// TestExcludesFromConfig locks the missing-vs-malformed distinction: a missing
// .tesser-build.yaml is not an error (no excludes), but a present-but-malformed one IS
// an error so the tool fails loud instead of silently disabling excludes.
func TestExcludesFromConfig(t *testing.T) {
	t.Run("missing file is not an error", func(t *testing.T) {
		dir := t.TempDir()
		got, err := excludesFromConfig(dir)
		if err != nil {
			t.Fatalf("missing config should not error, got %v", err)
		}
		if len(got) != 0 {
			t.Fatalf("missing config should yield no excludes, got %v", got)
		}
	})

	t.Run("valid file is parsed", func(t *testing.T) {
		dir := t.TempDir()
		writeConfig(t, dir, "exclude:\n  - Ledger\n  - Transaction\n")
		got, err := excludesFromConfig(dir)
		if err != nil {
			t.Fatalf("valid config errored: %v", err)
		}
		if !got["Ledger"] || !got["Transaction"] {
			t.Fatalf("expected Ledger+Transaction excluded, got %v", got)
		}
	})

	t.Run("malformed file is a loud error", func(t *testing.T) {
		dir := t.TempDir()
		// A list where a mapping is expected — yaml.Unmarshal rejects it.
		writeConfig(t, dir, "exclude:\n\t- bad tab indentation\n  not: valid: yaml:\n")
		got, err := excludesFromConfig(dir)
		if err == nil {
			t.Fatalf("malformed config must error (silent no-excludes is the bug), got %v", got)
		}
		if got != nil {
			t.Fatalf("malformed config must not return a partial set, got %v", got)
		}
	})
}

func writeConfig(t *testing.T, dir, body string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, ConfigName), []byte(body), 0o644); err != nil {
		t.Fatalf("write config: %v", err)
	}
}
