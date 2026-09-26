package experimentcorpus

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestGenerationDeterminismAndMetadata(t *testing.T) {
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		for _, variant := range []string{"structured", "scattered"} {
			t.Run(family+"/"+variant, func(t *testing.T) {
				first, second := t.TempDir(), filepath.Join(t.TempDir(), "new")
				for _, out := range []string{first, second} {
					if err := Generate(Options{Family: family, Variant: variant, Seed: 42, Out: out}); err != nil {
						t.Fatal(err)
					}
				}
				var metadata Metadata
				if err := json.Unmarshal(readGenerated(t, first, "metadata.json"), &metadata); err != nil {
					t.Fatal(err)
				}
				if metadata.Conformance != "unchecked" || metadata.Architecture != "intentionally-nonconformant-controlled-seed" || metadata.Seed != 42 || metadata.Family != family || metadata.Variant != variant {
					t.Fatalf("incorrect provenance: %+v", metadata)
				}
				for _, name := range []string{"application.py", "README.md", ".tesser-root", "metadata.json"} {
					content := readGenerated(t, first, name)
					if !bytes.Equal(content, readGenerated(t, second, name)) {
						t.Errorf("%s differs between identical invocations", name)
					}
					if name != "metadata.json" {
						digest := sha256.Sum256(content)
						if metadata.Digests[name] != hex.EncodeToString(digest[:]) {
							t.Errorf("%s digest mismatch", name)
						}
					}
				}
				if string(readGenerated(t, first, ".tesser-root")) != "app\n" {
					t.Fatal("tree declaration must not skip generated code")
				}
				if err := Generate(Options{Family: family, Variant: variant, Out: first}); err == nil {
					t.Fatal("overwrote nonempty output")
				}
			})
		}
	}
}

func TestRejectsUnsafeOutput(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "target")
	if err := os.Mkdir(target, 0o755); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(base, "link")
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(base, "file")
	if err := os.WriteFile(file, []byte("untouched"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, out := range []string{link, filepath.Join(link, "child"), file, filepath.Join(base, "missing", "child"), ""} {
		if err := Generate(Options{Family: "reserving-inventory", Variant: "structured", Out: out}); err == nil {
			t.Errorf("accepted unsafe output %q", out)
		}
	}
	if got := string(readGenerated(t, base, "file")); got != "untouched" {
		t.Fatalf("existing file changed: %q", got)
	}
	entries, err := os.ReadDir(target)
	if err != nil || len(entries) != 0 {
		t.Fatalf("symlink target changed: %v, %v", entries, err)
	}
}

func TestInvalidOptionsDoNotCreateOutput(t *testing.T) {
	for _, options := range []Options{{Family: "unknown", Variant: "structured"}, {Family: "reserving-inventory", Variant: "unknown"}} {
		options.Out = filepath.Join(t.TempDir(), "app")
		if err := Generate(options); err == nil {
			t.Fatal("invalid options accepted")
		}
		if _, err := os.Stat(options.Out); !os.IsNotExist(err) {
			t.Fatalf("invalid options created output: %v", err)
		}
	}
}

func readGenerated(t *testing.T, dir, name string) []byte {
	t.Helper()
	content, err := os.ReadFile(filepath.Join(dir, name))
	if err != nil {
		t.Fatal(err)
	}
	return content
}
