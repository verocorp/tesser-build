package main

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

// findingRE matches one tessercheck diagnostic line ("…/file.go:12:3: message").
var findingRE = regexp.MustCompile(`(?m)\.go:\d+:\d+:`)

func countFindings(out string) int { return len(findingRE.FindAllString(out, -1)) }

// TestE2E_ConsumerModule runs the real tessercheck binary against a self-contained
// consumer module (testdata/consumer) that reproduces the findings the quanta
// dogfood surfaced: a value object missing its canonical constructor
// (voconstructor), a genuine .String()-comparison hazard (stringequality), and
// the .String() shapes that must NOT fire (discarded call, literal compare,
// stdlib .String()). It also exercises the .tesser-build.yaml exclude path and the
// fail-loud-on-malformed-config behavior end-to-end — coverage the per-analyzer
// analysistest cannot give, because only a built binary against a real module
// has a config file, a build step, and an exit code.
func TestE2E_ConsumerModule(t *testing.T) {
	if testing.Short() {
		t.Skip("e2e builds a binary and shells out to go")
	}
	if _, err := exec.LookPath("go"); err != nil {
		t.Skip("go toolchain not on PATH")
	}

	// Build tessercheck from this package.
	bin := filepath.Join(t.TempDir(), "tessercheck")
	if out, err := exec.Command("go", "build", "-o", bin, ".").CombinedOutput(); err != nil {
		t.Fatalf("building tessercheck: %v\n%s", err, out)
	}

	// Copy the fixture to a writable temp module so the test owns its config.
	moduleDir := filepath.Join(t.TempDir(), "consumer")
	if err := os.CopyFS(moduleDir, os.DirFS("testdata/consumer")); err != nil {
		t.Fatalf("copying fixture: %v", err)
	}
	cfgPath := filepath.Join(moduleDir, ".tesser-build.yaml")

	run := func() (string, int) {
		t.Helper()
		cmd := exec.Command(bin, "./...")
		cmd.Dir = moduleDir
		out, err := cmd.CombinedOutput()
		if err != nil {
			var ee *exec.ExitError
			if !errors.As(err, &ee) {
				t.Fatalf("running tessercheck: %v\n%s", err, out)
			}
			return string(out), ee.ExitCode()
		}
		return string(out), 0
	}

	// Run A — Ledger excluded: exactly the two true positives, no false positives.
	if err := os.WriteFile(cfgPath, []byte("exclude:\n  - Ledger\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	out, code := run()
	if code == 0 {
		t.Errorf("run A: expected non-zero exit with findings, got 0\n%s", out)
	}
	if n := countFindings(out); n != 2 {
		t.Errorf("run A: want 2 findings, got %d\n%s", n, out)
	}
	if !(strings.Contains(out, "posted.go") && strings.Contains(out, "no validating constructor")) {
		t.Errorf("run A: missing voconstructor finding for Posted\n%s", out)
	}
	if !(strings.Contains(out, "money_test.go") && strings.Contains(out, "compare by value")) {
		t.Errorf("run A: missing stringequality finding\n%s", out)
	}
	// The conforming Money VO, the excluded Ledger, and the non-comparison
	// .String() uses must all stay silent.
	if strings.Contains(out, "money.go:") {
		t.Errorf("run A: conforming Money should not be flagged\n%s", out)
	}
	if strings.Contains(out, "ledger.go") {
		t.Errorf("run A: excluded Ledger should not be flagged\n%s", out)
	}

	// Run B — no config: Ledger is no longer excluded, so voconstructor flags it
	// too. Proves the .tesser-build.yaml exclude is load-bearing, not decorative.
	if err := os.Remove(cfgPath); err != nil {
		t.Fatal(err)
	}
	out, _ = run()
	if n := countFindings(out); n != 3 {
		t.Errorf("run B: want 3 findings (Posted, stringequality, Ledger), got %d\n%s", n, out)
	}
	if !(strings.Contains(out, "ledger.go") && strings.Contains(out, "no validating constructor")) {
		t.Errorf("run B: missing voconstructor finding for un-excluded Ledger\n%s", out)
	}

	// Run C — malformed config must fail loud, not silently fall back to "no
	// excludes" (the eng-review silent-gap fix).
	if err := os.WriteFile(cfgPath, []byte("exclude: [unterminated\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	out, code = run()
	if code == 0 {
		t.Errorf("run C: malformed config should fail loud, got exit 0\n%s", out)
	}
	if !strings.Contains(out, "malformed .tesser-build.yaml") {
		t.Errorf("run C: want a loud malformed-config error\n%s", out)
	}
}
