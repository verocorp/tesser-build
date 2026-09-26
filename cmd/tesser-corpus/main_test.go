package main

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestCLI(t *testing.T) {
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		for _, variant := range []string{"structured", "scattered"} {
			t.Run(family+"/"+variant, func(t *testing.T) {
				out := filepath.Join(t.TempDir(), "app")
				var stderr bytes.Buffer
				if code := run([]string{"--family", family, "--variant", variant, "--seed", "-3", "--out", out}, &stderr); code != 0 {
					t.Fatalf("exit %d: %s", code, &stderr)
				}
				if _, err := os.Stat(filepath.Join(out, "application.py")); err != nil {
					t.Fatal(err)
				}
			})
		}
	}
}

func TestCLIRejectsInvalidArguments(t *testing.T) {
	for _, args := range [][]string{nil, {"--family", "unknown"}, {"--seed", "not-an-integer"}, {"--unknown"}, {"positional"}} {
		var stderr bytes.Buffer
		if code := run(args, &stderr); code == 0 || stderr.Len() == 0 {
			t.Errorf("args %q: exit %d, stderr %q", args, code, stderr.String())
		}
	}
}
