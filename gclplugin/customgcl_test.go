package gclplugin_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

// gclVersionRE pulls "2.12.2" out of `golangci-lint version` output.
var gclVersionRE = regexp.MustCompile(`version v?(\d+\.\d+\.\d+)`)

// TestCustomGCL_BundlesAndRuns proves this package actually builds into a
// golangci-lint v2 custom binary and that the bundled dddvet linter runs
// end-to-end against real code. plugin_test.go covers the plugin's Go API
// (registry parity, load mode), but only `golangci-lint custom` exercises the
// module-plugin bundling — the editor-integration path the README documents.
//
// Skipped unless a golangci-lint v2 binary is on PATH (CI installs one); v1 has
// no module plugins. Like the cmd/ddd-vet e2e test, it builds a binary and
// shells out, so it is also -short-skippable.
func TestCustomGCL_BundlesAndRuns(t *testing.T) {
	if testing.Short() {
		t.Skip("builds a custom golangci-lint binary (compiles from source)")
	}
	gcl, err := exec.LookPath("golangci-lint")
	if err != nil {
		t.Skip("golangci-lint not on PATH")
	}
	verOut, err := exec.Command(gcl, "version").CombinedOutput()
	if err != nil {
		t.Skipf("golangci-lint version failed: %v\n%s", err, verOut)
	}
	m := gclVersionRE.FindStringSubmatch(string(verOut))
	if m == nil {
		t.Skipf("could not parse golangci-lint version from %q", verOut)
	}
	version := "v" + m[1]
	if !strings.HasPrefix(version, "v2.") {
		t.Skipf("module plugins need golangci-lint v2, found %s", version)
	}

	// Module root = dir of go.mod, so the plugin builds from this checkout.
	gomod, err := exec.Command("go", "env", "GOMOD").Output()
	if err != nil {
		t.Fatalf("go env GOMOD: %v", err)
	}
	moduleRoot := filepath.Dir(strings.TrimSpace(string(gomod)))
	work := t.TempDir()

	// 1. Build a custom golangci-lint with this checkout's plugin bundled via
	// path:, so we test the code on disk, not a published tag.
	customCfg := "version: " + version + "\n" +
		"name: custom-gcl\n" +
		"destination: " + work + "\n" +
		"plugins:\n" +
		"  - module: github.com/verocorp/go-ddd\n" +
		"    import: github.com/verocorp/go-ddd/gclplugin\n" +
		"    path: " + moduleRoot + "\n"
	if err := os.WriteFile(filepath.Join(work, ".custom-gcl.yml"), []byte(customCfg), 0o644); err != nil {
		t.Fatal(err)
	}
	build := exec.Command(gcl, "custom")
	build.Dir = work
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("golangci-lint custom (plugin failed to bundle): %v\n%s", err, out)
	}
	customGCL := filepath.Join(work, "custom-gcl")
	if _, err := os.Stat(customGCL); err != nil {
		t.Fatalf("custom-gcl binary not produced: %v", err)
	}

	// 2. Fixture module with one clear voconstructor violation; dddvet is the
	// only enabled linter so the assertion can't be perturbed by defaults.
	fix := filepath.Join(work, "fixture")
	if err := os.MkdirAll(fix, 0o755); err != nil {
		t.Fatal(err)
	}
	write := func(name, content string) {
		t.Helper()
		if err := os.WriteFile(filepath.Join(fix, name), []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	write("go.mod", "module fixture\n\ngo 1.25\n")
	write("vo.go", "package fixture\n\n"+
		"// Money is value-object-shaped (exported, only unexported fields) but has\n"+
		"// no validating constructor, so the voconstructor analyzer must flag it.\n"+
		"type Money struct{ amount int64 }\n")
	write(".golangci.yml", "version: \"2\"\n"+
		"linters:\n"+
		"  default: none\n"+
		"  enable:\n"+
		"    - dddvet\n"+
		"  settings:\n"+
		"    custom:\n"+
		"      dddvet:\n"+
		"        type: module\n"+
		"        description: DDD value-object analyzers (ddd-vet)\n")

	// 3. The bundled linter must surface the dddvet finding and exit non-zero.
	run := exec.Command(customGCL, "run", "./...")
	run.Dir = fix
	out, err := run.CombinedOutput()
	if err == nil {
		t.Errorf("custom-gcl run: expected non-zero exit (a finding), got 0\n%s", out)
	}
	got := string(out)
	if !strings.Contains(got, "(dddvet)") {
		t.Errorf("custom-gcl run: dddvet did not fire through the plugin\n%s", got)
	}
	if !strings.Contains(got, "no validating constructor") {
		t.Errorf("custom-gcl run: missing the voconstructor diagnostic\n%s", got)
	}
}
