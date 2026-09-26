package experiment_test

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
)

const contractJSON = `{
  "version":1,"id":"trial","family":"echo",
  "requirements":["Echo the objects."],"vocabulary":{"object":"JSON object"},
  "probes":[{"id":"base","inputs":[{"x":1},{"x":2}],"expected":[{"x":1},{"x":2}]}],
  "followups":[{"id":"secret-change","requirements":["Selected hidden requirement."],
    "probes":[{"id":"hidden-probe","inputs":[{"secret":"private-input"}],"expected":[{"secret":"private-answer"}]}]}]
}`

func optionsFor(t *testing.T, script string) experiment.Options {
	t.Helper()
	root := t.TempDir()
	candidate := filepath.Join(root, "candidate")
	if err := os.Mkdir(candidate, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(candidate, "main.sh"), []byte(script), 0644); err != nil {
		t.Fatal(err)
	}
	scenario := filepath.Join(root, "scenario.json")
	if err := os.WriteFile(scenario, []byte(contractJSON), 0600); err != nil {
		t.Fatal(err)
	}
	return experiment.Options{ScenarioPath: scenario, CandidateDir: candidate, Command: []string{"/bin/sh", "main.sh"}, Deadline: 3 * time.Second}
}

func TestVerifyProtocol(t *testing.T) {
	cases := []struct {
		name   string
		script string
		status string
		exit   int
		error  string
	}{
		{"correct", "cat", experiment.Correct, 0, ""},
		{"wrong", `printf '{"x":9}\n{"x":9}\n'`, experiment.Incorrect, 0, "differs"},
		{"malformed", `printf 'invalid\ninvalid\n'`, experiment.Incorrect, 0, "valid JSON"},
		{"extra", `cat; printf '{}\n'`, experiment.Incorrect, 0, "response count"},
		{"missing", `printf '{"x":1}\n'`, experiment.Incorrect, 0, "response count"},
		{"empty", "true", experiment.Incorrect, 0, "response count"},
		{"blank", `cat; printf '\n'`, experiment.Incorrect, 0, "response count"},
		{"array", `printf '[]\n[]\n'`, experiment.Incorrect, 0, "valid JSON"},
		{"null", `printf 'null\nnull\n'`, experiment.Incorrect, 0, "valid JSON"},
		{"two-on-line", `printf '{} {}\n{}\n'`, experiment.Incorrect, 0, "valid JSON"},
		{"duplicate-keys", `printf '{"x":8,"x":1}\n{"x":2}\n'`, experiment.Incorrect, 0, "duplicate"},
		{"nonzero-after-correct", "cat; echo failure >&2; exit 7", experiment.Incorrect, 7, "exit status 7"},
		{"mutation", "touch generated; cat", experiment.Incorrect, 0, "snapshot changed"},
		{"transient-mutation", "touch generated; rm generated; cat", experiment.Incorrect, 0, "snapshot changed"},
		{"rewrite-same-content", "cat main.sh > temporary; cat temporary > main.sh; rm temporary; cat", experiment.Incorrect, 0, "snapshot changed"},
		{"normalized-numbers", `printf '{"x":1.000e+0}\n{"x":0.2e1}\n'`, experiment.Correct, 0, ""},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			options := optionsFor(t, test.script)
			result := experiment.Verify(context.Background(), options)
			if result.Status != test.status || !result.Eligible || len(result.Stages) != 1 {
				t.Fatalf("unexpected result: %+v", result)
			}
			stage := result.Stages[0]
			if stage.ExitCode == nil || *stage.ExitCode != test.exit || !strings.Contains(stage.Error, test.error) {
				t.Fatalf("unexpected stage: %+v", stage)
			}
			if stage.Status != result.Status {
				t.Fatalf("stage failure was masked: %+v", result)
			}
			if _, err := os.Stat(filepath.Join(options.CandidateDir, "generated")); !os.IsNotExist(err) {
				t.Fatalf("candidate source was modified: %v", err)
			}
		})
	}
}

func TestVerifyEvidence(t *testing.T) {
	options := optionsFor(t, "cat")
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct || len(result.SourceDigest) != 64 || len(result.ContractDigest) != 64 {
		t.Fatalf("missing proof: %+v", result)
	}
	if result.Usage != "unknown" || result.Cost != "unknown" || result.HumanIntervention != "unknown" {
		t.Fatalf("unmeasured evidence claimed: %+v", result)
	}
	if result.VerificationStartedAt.IsZero() || result.VerificationEndedAt.Before(result.VerificationStartedAt) || result.VerificationElapsedMS < 0 || result.VerificationBudgetMS != 3000 {
		t.Fatalf("invalid verification timings: %+v", result)
	}
	encoded, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(encoded), "completion") || strings.Contains(string(encoded), "autonomous") {
		t.Fatalf("verifier claimed task-level measurements: %s", encoded)
	}
	repeated := experiment.Verify(context.Background(), options)
	if repeated.SourceDigest != result.SourceDigest || repeated.ContractDigest != result.ContractDigest {
		t.Fatal("stable input did not produce stable digests")
	}
}

func TestVerifyRejectsHardlinksRatherThanChangingTheirIdentity(t *testing.T) {
	options := optionsFor(t, "cat")
	if err := os.WriteFile(filepath.Join(options.CandidateDir, "original"), []byte("content"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Link(filepath.Join(options.CandidateDir, "original"), filepath.Join(options.CandidateDir, "alias")); err != nil {
		t.Fatal(err)
	}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.InfraError || result.Eligible || !strings.Contains(result.Error, "hard-linked") {
		t.Fatalf("hard links must not be represented as independent files: %+v", result)
	}
}

func TestVerifyPreservesSourceModificationTimes(t *testing.T) {
	options := optionsFor(t, "python3 -B -c 'import os,time,sys; sys.exit(0 if time.time()-os.stat(\"data\").st_mtime > 3600 else 8)' || exit 8\ncat")
	path := filepath.Join(options.CandidateDir, "data")
	if err := os.WriteFile(path, []byte("content"), 0644); err != nil {
		t.Fatal(err)
	}
	old := time.Now().Add(-2 * time.Hour)
	if err := os.Chtimes(path, old, old); err != nil {
		t.Fatal(err)
	}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct {
		t.Fatalf("candidate ran against a different modification time: %+v", result)
	}
}

func TestVerifyTimeoutAndSharedBudget(t *testing.T) {
	options := optionsFor(t, "sleep 5; cat")
	options.Deadline = 80 * time.Millisecond
	start := time.Now()
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Timeout || time.Since(start) > 2*time.Second || len(result.Stages) != 1 {
		t.Fatalf("deadline not enforced: %+v", result)
	}
	if result.Stages[0].ExitCode == nil || *result.Stages[0].ExitCode != -1 {
		t.Fatalf("missing actual timeout exit: %+v", result.Stages[0])
	}
	options = optionsFor(t, "cat")
	options.Gates = [][]string{{"/bin/sh", "-c", "sleep 0.1"}, {"/bin/sh", "-c", "sleep 0.1"}}
	options.Deadline = 150 * time.Millisecond
	result = experiment.Verify(context.Background(), options)
	if result.Status != experiment.Timeout || len(result.Stages) != 2 || result.Stages[0].Status != experiment.Correct || result.Stages[1].Status != experiment.Timeout {
		t.Fatalf("gates did not share the deadline: %+v", result)
	}
}

func TestVerifyGateFailureAndMutationAreNotMasked(t *testing.T) {
	for _, script := range []string{"echo gate-failed >&2; exit 9", "touch changed"} {
		options := optionsFor(t, "cat")
		options.Gates = [][]string{{"/bin/sh", "-c", script}}
		result := experiment.Verify(context.Background(), options)
		if result.Status != experiment.Incorrect || len(result.Stages) != 1 || result.Stages[0].Kind != "gate" {
			t.Fatalf("gate failure masked: %+v", result)
		}
	}
}

func TestVerifySnapshotIsStableAndShared(t *testing.T) {
	options := optionsFor(t, "cat")
	outside := t.TempDir()
	gateLocation := filepath.Join(outside, "gate-location")
	probeLocation := filepath.Join(outside, "probe-location")
	script := "printf '%s' \"$PWD\" > \"$1\"; cat"
	if err := os.WriteFile(filepath.Join(options.CandidateDir, "main.sh"), []byte(script), 0644); err != nil {
		t.Fatal(err)
	}
	options.Command = []string{"/bin/sh", filepath.Join(options.CandidateDir, "main.sh"), probeLocation}
	options.Gates = [][]string{{"/bin/sh", "-c", `printf '%s' "$PWD" > "$1"; printf 'exit 12' > "$2"`, "gate", gateLocation, filepath.Join(outside, "unused")}}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct {
		t.Fatalf("verification failed: %+v", result)
	}
	gateDirectory, err := os.ReadFile(gateLocation)
	if err != nil {
		t.Fatal(err)
	}
	probeDirectory, err := os.ReadFile(probeLocation)
	if err != nil {
		t.Fatal(err)
	}
	if string(gateDirectory) == options.CandidateDir || string(gateDirectory) != string(probeDirectory) {
		t.Fatalf("stages did not share the copied snapshot: %q %q", gateDirectory, probeDirectory)
	}
	if _, err := os.Stat(string(gateDirectory)); !os.IsNotExist(err) {
		t.Fatalf("owned snapshot was not removed: %v", err)
	}
}

func TestVerifyOriginalMutationCannotChangeSnapshot(t *testing.T) {
	options := optionsFor(t, "cat")
	mutate := filepath.Join(t.TempDir(), "mutate.sh")
	script := fmt.Sprintf("printf 'exit 17' > %q", filepath.Join(options.CandidateDir, "main.sh"))
	if err := os.WriteFile(mutate, []byte(script), 0600); err != nil {
		t.Fatal(err)
	}
	options.Gates = [][]string{{"/bin/sh", mutate}}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct {
		t.Fatalf("original source changed the copied snapshot: %+v", result)
	}
	if got, err := os.ReadFile(filepath.Join(options.CandidateDir, "main.sh")); err != nil || string(got) != "exit 17" {
		t.Fatalf("test did not mutate the original source: %q %v", got, err)
	}
}

func TestVerifyRemapsCandidateArgumentsThroughParentAliases(t *testing.T) {
	options := optionsFor(t, "cat")
	alias := filepath.Join(t.TempDir(), "parent")
	if err := os.Symlink(filepath.Dir(options.CandidateDir), alias); err != nil {
		t.Fatal(err)
	}
	options.CandidateDir = filepath.Join(alias, "candidate")
	options.Command = []string{"/bin/sh", filepath.Join(options.CandidateDir, "main.sh")}
	mutate := filepath.Join(t.TempDir(), "mutate.sh")
	script := fmt.Sprintf("printf 'exit 17' > %q", filepath.Join(options.CandidateDir, "main.sh"))
	if err := os.WriteFile(mutate, []byte(script), 0600); err != nil {
		t.Fatal(err)
	}
	options.Gates = [][]string{{"/bin/sh", mutate}}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct {
		t.Fatalf("candidate alias executed outside the snapshot: %+v", result)
	}
}

func TestVerifyFailClosed(t *testing.T) {
	cases := []struct {
		name   string
		change func(*testing.T, *experiment.Options)
	}{
		{"missing-contract", func(t *testing.T, o *experiment.Options) { o.ScenarioPath += ".missing" }},
		{"unknown-followup", func(t *testing.T, o *experiment.Options) { o.Followup = "unknown" }},
		{"zero-budget", func(t *testing.T, o *experiment.Options) { o.Deadline = 0 }},
		{"negative-budget", func(t *testing.T, o *experiment.Options) { o.Deadline = -time.Second }},
		{"no-command", func(t *testing.T, o *experiment.Options) { o.Command = nil }},
		{"empty-command", func(t *testing.T, o *experiment.Options) { o.Command = []string{""} }},
		{"nul-command", func(t *testing.T, o *experiment.Options) { o.Command = []string{"cat", "\x00"} }},
		{"invalid-gate", func(t *testing.T, o *experiment.Options) { o.Gates = [][]string{nil} }},
		{"empty-candidate", func(t *testing.T, o *experiment.Options) { o.CandidateDir = "" }},
		{"symlink", func(t *testing.T, o *experiment.Options) {
			if err := os.Symlink(o.ScenarioPath, filepath.Join(o.CandidateDir, "linked")); err != nil {
				t.Fatal(err)
			}
		}},
		{"root-symlink", func(t *testing.T, o *experiment.Options) {
			link := filepath.Join(t.TempDir(), "linked")
			if err := os.Symlink(o.CandidateDir, link); err != nil {
				t.Fatal(err)
			}
			o.CandidateDir = link
		}},
		{"oracle-in-candidate", func(t *testing.T, o *experiment.Options) {
			o.ScenarioPath = filepath.Join(o.CandidateDir, "oracle.json")
			if err := os.WriteFile(o.ScenarioPath, []byte(contractJSON), 0600); err != nil {
				t.Fatal(err)
			}
		}},
		{"recursive-temp", func(t *testing.T, o *experiment.Options) { t.Setenv("TMPDIR", o.CandidateDir) }},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			options := optionsFor(t, "cat")
			test.change(t, &options)
			result := experiment.Verify(context.Background(), options)
			if result.Status != experiment.InfraError || result.Error == "" || result.Eligible || len(result.Stages) != 0 {
				t.Fatalf("invalid run accepted: %+v", result)
			}
		})
	}
}

func TestVerifyMissingExecutable(t *testing.T) {
	options := optionsFor(t, "cat")
	options.Command = []string{filepath.Join(t.TempDir(), "missing")}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.InfraError || len(result.Stages) != 1 || result.Stages[0].ExitCode != nil || result.Stages[0].Error == "" {
		t.Fatalf("missing executable misreported: %+v", result)
	}
}

func TestVerifyFollowupIncludesBaseAndFreshProcesses(t *testing.T) {
	options := optionsFor(t, "cat")
	options.Followup = "secret-change"
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Incorrect || len(result.Stages) != 2 || result.Stages[0].ID != "base" || result.Stages[0].Status != experiment.Correct || result.Stages[1].ID != "hidden-probe" {
		t.Fatalf("followup did not verify base plus change: %+v", result)
	}
	options = optionsFor(t, `i=0; while read -r line; do i=$((i+1)); printf '{"x":%d}\n' "$i"; done`)
	scenario := strings.Replace(contractJSON, `{"secret":"private-input"}`, `{"x":1}`, 1)
	scenario = strings.Replace(scenario, `{"secret":"private-answer"}`, `{"x":1}`, 1)
	if err := os.WriteFile(options.ScenarioPath, []byte(scenario), 0600); err != nil {
		t.Fatal(err)
	}
	options.Followup = "secret-change"
	result = experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct || len(result.Stages) != 2 {
		t.Fatalf("probes did not start fresh processes: %+v", result)
	}
}

func TestVerifyBoundedStderr(t *testing.T) {
	options := optionsFor(t, "i=0; while [ $i -lt 5000 ]; do printf 'evidence' >&2; i=$((i+1)); done; cat")
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct || len(result.Stages) != 1 {
		t.Fatalf("verification failed: %+v", result)
	}
	stage := result.Stages[0]
	if len(stage.Stderr) != 16<<10 || !stage.StderrTruncated || !strings.HasPrefix(stage.Stderr, "evidence") {
		t.Fatalf("stderr was not bounded: %d bytes, truncated=%v", len(stage.Stderr), stage.StderrTruncated)
	}
}

func TestVerifyRejectsSpecialFiles(t *testing.T) {
	options := optionsFor(t, "cat")
	if err := syscall.Mkfifo(filepath.Join(options.CandidateDir, "pipe"), 0600); err != nil {
		t.Fatal(err)
	}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.InfraError || !strings.Contains(result.Error, "special file") {
		t.Fatalf("special file was accepted: %+v", result)
	}
	options = optionsFor(t, "cat")
	options.ScenarioPath = filepath.Join(t.TempDir(), "contract-pipe")
	if err := syscall.Mkfifo(options.ScenarioPath, 0600); err != nil {
		t.Fatal(err)
	}
	result = experiment.Verify(context.Background(), options)
	if result.Status != experiment.InfraError || !strings.Contains(result.Error, "regular JSON file") {
		t.Fatalf("nonregular contract was accepted: %+v", result)
	}
}

func TestVerifyKillsDescendantsOnTimeout(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("python3 is required for the descendant-process fixture")
	}
	options := optionsFor(t, "cat")
	marker := filepath.Join(t.TempDir(), "survived")
	fixture := "import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', 'import pathlib,sys,time; time.sleep(0.4); pathlib.Path(sys.argv[1]).write_text(\"alive\")', sys.argv[1]])\ntime.sleep(5)\n"
	if err := os.WriteFile(filepath.Join(options.CandidateDir, "process.py"), []byte(fixture), 0600); err != nil {
		t.Fatal(err)
	}
	options.Command = []string{python, "-B", "process.py", marker}
	options.Deadline = 150 * time.Millisecond
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Timeout {
		t.Fatalf("fixture did not time out: %+v", result)
	}
	time.Sleep(500 * time.Millisecond)
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatalf("descendant survived process-group cancellation: %v", err)
	}
}

func TestVerifyCapsStdout(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("python3 is required for the output-limit fixture")
	}
	options := optionsFor(t, "cat")
	options.Command = []string{python, "-B", "-c", "import sys; sys.stdout.write('x' * (5 * 1024 * 1024))"}
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Incorrect || !strings.Contains(result.Error, "stdout exceeds") {
		t.Fatalf("unbounded stdout accepted: %+v", result)
	}
}

func TestVerifyContextCancellation(t *testing.T) {
	options := optionsFor(t, "cat")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result := experiment.Verify(ctx, options)
	if result.Status != experiment.InfraError || result.Eligible || len(result.Stages) != 0 {
		t.Fatalf("canceled run was executed: %+v", result)
	}
}
