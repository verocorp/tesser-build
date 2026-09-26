package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/verocorp/tesser-build/internal/experiment"
)

const cliContract = `{"version":1,"id":"cli","family":"echo","requirements":["Echo objects."],"vocabulary":{},"probes":[{"id":"base","inputs":[{"value":1}],"expected":[{"value":1}]}],"followups":[{"id":"undisclosed","requirements":["Secret change."],"probes":[{"id":"hidden","inputs":[{"private":true}],"expected":[{"private":false}]}]}]}`

func cliPaths(t *testing.T) (string, string, string) {
	t.Helper()
	root := t.TempDir()
	candidate := filepath.Join(root, "candidate")
	if err := os.Mkdir(candidate, 0755); err != nil {
		t.Fatal(err)
	}
	scenario := filepath.Join(root, "scenario.json")
	if err := os.WriteFile(scenario, []byte(cliContract), 0600); err != nil {
		t.Fatal(err)
	}
	return scenario, candidate, filepath.Join(root, "result.json")
}

func TestCLIResultsAndExitCodes(t *testing.T) {
	cases := []struct {
		name    string
		command string
		status  string
		code    int
	}{
		{"correct", `["/bin/cat"]`, experiment.Correct, 0},
		{"wrong", `["/bin/echo","{}"]`, experiment.Incorrect, 1},
		{"nonzero", `["/bin/sh","-c","exit 6"]`, experiment.Incorrect, 1},
		{"timeout", `["/bin/sh","-c","sleep 5"]`, experiment.Timeout, 1},
		{"missing-executable", `["/nonexistent/tesser-fixture"]`, experiment.InfraError, 1},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			scenario, candidate, path := cliPaths(t)
			var stdout, stderr bytes.Buffer
			code := run(context.Background(), []string{"verify", "--scenario", scenario, "--candidate", candidate, "--command-json", test.command, "--result", path, "--deadline", "200ms"}, &stdout, &stderr)
			if code != test.code {
				t.Fatalf("exit=%d want=%d stderr=%s", code, test.code, stderr.String())
			}
			data, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			var result experiment.Result
			if err := json.Unmarshal(data, &result); err != nil {
				t.Fatal(err)
			}
			if result.Status != test.status || result.Usage != "unknown" || result.VerificationBudgetMS != 200 {
				t.Fatalf("wrong result: %s", data)
			}
		})
	}
}

func TestCLIMissingContractWritesInfrastructureResult(t *testing.T) {
	scenario, candidate, path := cliPaths(t)
	var output bytes.Buffer
	code := run(context.Background(), []string{"verify", "--scenario", scenario + ".missing", "--candidate", candidate, "--command-json", `["/bin/cat"]`, "--result", path, "--deadline", "1s"}, &output, &output)
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var result experiment.Result
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatal(err)
	}
	if code == 0 || result.Status != experiment.InfraError || result.Eligible || result.Error == "" {
		t.Fatalf("missing contract accepted: %s", data)
	}
}

func TestCLIBriefHidesFollowupsAndOracle(t *testing.T) {
	scenario, _, _ := cliPaths(t)
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"brief", "--scenario", scenario}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("brief failed: %s", stderr.String())
	}
	for _, hidden := range []string{"undisclosed", "Secret change.", "private", `"probes"`, `"expected"`} {
		if strings.Contains(stdout.String(), hidden) {
			t.Fatalf("brief exposed %q: %s", hidden, stdout.String())
		}
	}
	stdout.Reset()
	code = run(context.Background(), []string{"brief", "--scenario", scenario, "--followup", "undisclosed"}, &stdout, &stderr)
	if code != 0 || !strings.Contains(stdout.String(), "Secret change.") || strings.Contains(stdout.String(), "private") {
		t.Fatalf("selected brief wrong: %s stderr=%s", stdout.String(), stderr.String())
	}
	code = run(context.Background(), []string{"brief", "--scenario", scenario, "--followup", "unknown"}, &stdout, &stderr)
	if code == 0 {
		t.Fatal("unknown followup accepted")
	}
}

func TestCLIRejectsInvalidArguments(t *testing.T) {
	scenario, candidate, path := cliPaths(t)
	base := []string{"verify", "--scenario", scenario, "--candidate", candidate, "--command-json", `["/bin/cat"]`, "--result", path, "--deadline", "1s"}
	cases := [][]string{
		nil,
		{"unknown"},
		{"brief"},
		{"verify", "--scenario", scenario},
		append(append([]string{}, base...), "positional"),
		append(append([]string{}, base...), "--deadline", "0s"),
		append(append([]string{}, base...), "--deadline", "-1s"),
		append(append([]string{}, base...), "--deadline", "bad"),
		append(append([]string{}, base...), "--command-json", `"cat"`),
		append(append([]string{}, base...), "--command-json", `[]`),
		append(append([]string{}, base...), "--command-json", `[1]`),
		append(append([]string{}, base...), "--command-json", `["cat",null]`),
		append(append([]string{}, base...), "--gate-json", `null`),
		append(append([]string{}, base...), "--gate-json", `["cat"]`),
		append(append([]string{}, base...), "--gate-json", `[["cat",null]]`),
		append(append([]string{}, base...), "--result", filepath.Join(candidate, "result.json")),
		append(append([]string{}, base...), "--result", scenario),
	}
	for _, args := range cases {
		var output bytes.Buffer
		if code := run(context.Background(), args, &output, &output); code == 0 {
			t.Fatalf("invalid args accepted: %q", args)
		}
	}
	data, err := os.ReadFile(scenario)
	if err != nil || string(data) != cliContract {
		t.Fatalf("scenario overwritten: %s %v", data, err)
	}
}

func TestCLIResultParentSymlinkCannotEnterCandidate(t *testing.T) {
	scenario, candidate, path := cliPaths(t)
	link := filepath.Join(filepath.Dir(path), "alias")
	if err := os.Symlink(candidate, link); err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	code := run(context.Background(), []string{"verify", "--scenario", scenario, "--candidate", candidate, "--command-json", `["/bin/cat"]`, "--result", filepath.Join(link, "result.json"), "--deadline", "1s"}, &output, &output)
	if code == 0 || !strings.Contains(output.String(), "outside") {
		t.Fatalf("result alias accepted: %s", output.String())
	}
}

func TestCLIDoesNotInterpolateCommandArguments(t *testing.T) {
	scenario, candidate, path := cliPaths(t)
	marker := filepath.Join(t.TempDir(), "must-not-exist")
	command, err := json.Marshal([]string{"/bin/echo", "$(touch " + marker + ")"})
	if err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	code := run(context.Background(), []string{"verify", "--scenario", scenario, "--candidate", candidate, "--command-json", string(command), "--result", path, "--deadline", "1s"}, &output, &output)
	if code == 0 {
		t.Fatal("non-JSON output accepted")
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatalf("shell argument was interpolated: %v", err)
	}
}
