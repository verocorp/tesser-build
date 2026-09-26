package agentlab_test

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/verocorp/tesser-build/internal/experiment"
	"github.com/verocorp/tesser-build/internal/experimentcorpus"
)

func TestControlledProducersMeetIndependentContracts(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal("controlled corpus acceptance requires python3:", err)
	}
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		for _, variant := range []string{"structured", "scattered"} {
			for _, seed := range []int64{0, 1} {
				t.Run(family+"/"+variant+"/"+strconv.FormatInt(seed, 10), func(t *testing.T) {
					candidate := filepath.Join(t.TempDir(), "candidate")
					if err := experimentcorpus.Generate(experimentcorpus.Options{
						Family: family, Variant: variant, Seed: seed, Out: candidate,
					}); err != nil {
						t.Fatal(err)
					}
					result := experiment.Verify(context.Background(), experiment.Options{
						ScenarioPath: filepath.Join("scenarios", family+".json"),
						CandidateDir: candidate, Command: []string{python, "-B", "application.py"}, Deadline: 15 * time.Second,
					})
					if result.Status != experiment.Correct {
						t.Fatalf("independent acceptance: %s: %s", result.Status, result.Error)
					}
				})
			}
		}
	}
}

func TestIndependentContractsRejectKnownBehaviorFaults(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal("controlled corpus acceptance requires python3:", err)
	}
	cases := []struct {
		name   string
		family string
		before string
		after  string
	}{
		{
			name: "reservation-changes-wrong-state", family: "reserving-inventory",
			before: "self.reserved += quantity", after: "self.stock += quantity",
		},
		{
			name: "shipping-forgets-reservations", family: "reserving-inventory",
			before: "quantity > self.stock - self.reserved", after: "quantity > self.stock",
		},
		{
			name: "release-mutates-on-failure", family: "reserving-inventory",
			before: "return {\"error\": \"insufficient_reserved\"}",
			after:  "self.reserved = 0\n            return {\"error\": \"insufficient_reserved\"}",
		},
		{
			name: "transfer-credits-wrong-identity", family: "transferring-funds",
			before: "self.accounts[destination] += amount", after: "self.accounts[source] += amount",
		},
		{
			name: "transfer-duplicates-credit", family: "transferring-funds",
			before: "self.accounts[destination] += amount", after: "self.accounts[destination] += 2 * amount",
		},
		{
			name: "transfer-partially-writes-on-rejection", family: "transferring-funds",
			before: "return {\"error\": \"insufficient_funds\"}",
			after:  "self.accounts[source] -= amount\n            return {\"error\": \"insufficient_funds\"}",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			candidate := filepath.Join(t.TempDir(), "candidate")
			if err := experimentcorpus.Generate(experimentcorpus.Options{
				Family: tc.family, Variant: "structured", Out: candidate,
			}); err != nil {
				t.Fatal(err)
			}
			path := filepath.Join(candidate, "application.py")
			source, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if strings.Count(string(source), tc.before) != 1 {
				t.Fatal("fault injection must match exactly one policy site")
			}
			if err := os.WriteFile(path, []byte(strings.Replace(string(source), tc.before, tc.after, 1)), 0644); err != nil {
				t.Fatal(err)
			}
			result := experiment.Verify(context.Background(), experiment.Options{
				ScenarioPath: filepath.Join("scenarios", tc.family+".json"),
				CandidateDir: candidate, Command: []string{python, "-B", "application.py"}, Deadline: 15 * time.Second,
			})
			if result.Status != experiment.Incorrect || !strings.Contains(result.Error, "differs from the contract") {
				t.Fatalf("fault must fail behavioral assertions, not crash: %s: %s", result.Status, result.Error)
			}
		})
	}
}

func TestWithheldChangesRejectSingleEntryPathUpdates(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal("controlled corpus acceptance requires python3:", err)
	}
	cases := []struct {
		family, followup, before, after, killedBy string
	}{
		{
			family: "reserving-inventory", followup: "reserving-inventory--minimum-available",
			before:   "def ship(state, quantity):\n    if quantity > state.stock - state.reserved:",
			after:    "def ship(state, quantity):\n    if quantity > state.stock - state.reserved - 2:",
			killedBy: "reserving-inventory--reserve-boundary",
		},
		{
			family: "transferring-funds", followup: "transferring-funds--flat-fee",
			before:   "def purchase(state, amount):\n    if amount > state.accounts[\"amber\"]:\n        return {\"error\": \"insufficient_funds\"}\n    state.accounts[\"amber\"] -= amount",
			after:    "def purchase(state, amount):\n    if amount + 2 > state.accounts[\"amber\"]:\n        return {\"error\": \"insufficient_funds\"}\n    state.accounts[\"amber\"] -= amount + 2",
			killedBy: "transferring-funds--round-trip",
		},
	}
	for _, tc := range cases {
		t.Run(tc.family, func(t *testing.T) {
			candidate := filepath.Join(t.TempDir(), "candidate")
			if err := experimentcorpus.Generate(experimentcorpus.Options{
				Family: tc.family, Variant: "scattered", Seed: 1, Out: candidate,
			}); err != nil {
				t.Fatal(err)
			}
			options := experiment.Options{
				ScenarioPath: filepath.Join("scenarios", tc.family+".json"),
				CandidateDir: candidate, Command: []string{python, "-B", "application.py"}, Deadline: 15 * time.Second,
			}
			if base := experiment.Verify(context.Background(), options); base.Status != experiment.Correct {
				t.Fatalf("starting implementation must be admitted: %+v", base)
			}
			path := filepath.Join(candidate, "application.py")
			source, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if strings.Count(string(source), tc.before) != 1 {
				t.Fatal("fault injection must match exactly one entry path")
			}
			if err := os.WriteFile(path, []byte(strings.Replace(string(source), tc.before, tc.after, 1)), 0644); err != nil {
				t.Fatal(err)
			}
			options.Followup = tc.followup
			result := experiment.Verify(context.Background(), options)
			if result.Status != experiment.Incorrect || len(result.Stages) == 0 || result.Stages[len(result.Stages)-1].ID != tc.killedBy {
				t.Fatalf("one-path update escaped protected base inputs: %+v", result)
			}
		})
	}
}
