package experimentcorpus

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestInventoryProcessInvariantsAndEdges(t *testing.T) {
	commands := []string{
		`{"op":"status"}`,
		`{"op":"reserve","quantity":7}`,
		`{"op":"ship","quantity":4}`,
		`{"op":"status"}`,
		`{"op":"ship","quantity":3}`,
		`{"op":"reserve","quantity":1}`,
		`{"op":"release","quantity":8}`,
		`{"op":"release","quantity":7}`,
		`{"op":"ship","quantity":7}`,
		`{"op":"restock","quantity":1000}`,
		`{"op":"reserve","quantity":1000}`,
		`{"op":"release","quantity":1000}`,
		`{"op":"ship","quantity":1000}`,
	}
	want := []string{
		`{"stock":10,"reserved":0,"available":10}`,
		`{"stock":10,"reserved":7,"available":3}`,
		`{"error":"insufficient_stock"}`,
		`{"stock":10,"reserved":7,"available":3}`,
		`{"stock":7,"reserved":7,"available":0}`,
		`{"error":"insufficient_stock"}`,
		`{"error":"insufficient_reserved"}`,
		`{"stock":7,"reserved":0,"available":7}`,
		`{"stock":0,"reserved":0,"available":0}`,
		`{"stock":1000,"reserved":0,"available":1000}`,
		`{"stock":1000,"reserved":1000,"available":0}`,
		`{"stock":1000,"reserved":0,"available":1000}`,
		`{"stock":0,"reserved":0,"available":0}`,
	}
	assertAllImplementations(t, "reserving-inventory", commands, want)
}

func TestFundsProcessAtomicityAndConservation(t *testing.T) {
	commands := []string{
		`{"op":"balances"}`,
		`{"op":"transfer","from":"birch","to":"amber","amount":40}`,
		`{"op":"transfer","from":"birch","to":"amber","amount":1}`,
		`{"op":"balances"}`,
		`{"op":"purchase","amount":141}`,
		`{"op":"balances"}`,
		`{"op":"purchase","amount":140}`,
		`{"op":"purchase","amount":1}`,
		`{"op":"transfer","from":"birch","to":"amber","amount":140}`,
		`{"op":"purchase","amount":1}`,
		`{"op":"purchase","amount":1000}`,
		`{"op":"balances"}`,
	}
	want := []string{
		`{"amber":100,"birch":40}`, `{"amber":140,"birch":0}`,
		`{"error":"insufficient_funds"}`, `{"amber":140,"birch":0}`,
		`{"error":"insufficient_funds"}`, `{"amber":140,"birch":0}`,
		`{"amber":0,"birch":140}`, `{"error":"insufficient_funds"}`,
		`{"amber":140,"birch":0}`, `{"amber":139,"birch":1}`,
		`{"error":"insufficient_funds"}`, `{"amber":139,"birch":1}`,
	}
	assertAllImplementations(t, "transferring-funds", commands, want)
}

func TestMalformedCommandsDoNotMutateEitherFamily(t *testing.T) {
	common := []string{`null`, `true`, `[]`, `1`, `"status"`, `{}`, `{"op":null}`, `{"op":[]}`, `{"op":1}`, `{"op":"unknown"}`, `{`, ``, `{"op":"status","op":"status"}`, `NaN`}
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		invalid := append([]string{}, common...)
		status, initial := `{"op":"status"}`, `{"stock":10,"reserved":0,"available":10}`
		if family == "reserving-inventory" {
			invalid = append(invalid, `{"op":"status","quantity":1}`, `{"op":"reserve"}`, `{"op":"release","quantity":1,"extra":0}`)
			for _, operation := range []string{"reserve", "ship", "release", "restock"} {
				for _, value := range []string{"0", "-1", "1001", "true", "false", "null", "1.0", `"1"`, "[]", "{}", "1e999", "NaN"} {
					invalid = append(invalid, fmt.Sprintf(`{"op":%q,"quantity":%s}`, operation, value))
				}
			}
		} else {
			status, initial = `{"op":"balances"}`, `{"amber":100,"birch":40}`
			invalid = append(invalid, `{"op":"balances","amount":1}`, `{"op":"purchase"}`, `{"op":"purchase","amount":1,"from":"amber"}`, `{"op":"transfer","amount":1}`)
			for _, value := range []string{"0", "-1", "1001", "true", "false", "null", "1.0", `"1"`, "[]", "{}", "1e999", "NaN"} {
				invalid = append(invalid, fmt.Sprintf(`{"op":"purchase","amount":%s}`, value), fmt.Sprintf(`{"op":"transfer","from":"amber","to":"birch","amount":%s}`, value))
			}
			for _, value := range []string{`"cedar"`, "true", "null", "[]", "{}", "1"} {
				invalid = append(invalid, fmt.Sprintf(`{"op":"transfer","from":%s,"to":"birch","amount":1000}`, value), fmt.Sprintf(`{"op":"transfer","from":"amber","to":%s,"amount":1000}`, value))
			}
			invalid = append(invalid, `{"op":"transfer","from":"amber","to":"amber","amount":1000}`, `{"op":"transfer","from":"amber","to":"birch","amount":1000,"extra":true}`)
		}
		var commands, want []string
		for _, command := range invalid {
			commands = append(commands, command, status)
			want = append(want, `{"error":"invalid_input"}`, initial)
		}
		assertAllImplementations(t, family, commands, want)
	}
}

func TestDeterministicSequencesMatchIndependentStateModels(t *testing.T) {
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		random := rand.New(rand.NewSource(718))
		var commands, want []string
		stock, reserved, amber, birch := 10, 0, 100, 40
		for range 300 {
			value := random.Intn(1000) + 1
			if family == "reserving-inventory" {
				operation := []string{"reserve", "ship", "release", "restock"}[random.Intn(4)]
				commands = append(commands, fmt.Sprintf(`{"op":%q,"quantity":%d}`, operation, value), `{"op":"status"}`)
				errorCode := ""
				switch operation {
				case "reserve", "ship":
					if value > stock-reserved {
						errorCode = "insufficient_stock"
					} else if operation == "reserve" {
						reserved += value
					} else {
						stock -= value
					}
				case "release":
					if value > reserved {
						errorCode = "insufficient_reserved"
					} else {
						reserved -= value
					}
				case "restock":
					stock += value
				}
				if stock < reserved || reserved < 0 {
					t.Fatal("model violated inventory invariant")
				}
				status := fmt.Sprintf(`{"stock":%d,"reserved":%d,"available":%d}`, stock, reserved, stock-reserved)
				result := status
				if errorCode != "" {
					result = fmt.Sprintf(`{"error":%q}`, errorCode)
				}
				want = append(want, result, status)
			} else {
				value = random.Intn(160) + 1
				operation := random.Intn(3)
				command := fmt.Sprintf(`{"op":"purchase","amount":%d}`, value)
				from, to := "amber", "birch"
				if operation == 2 {
					from, to = to, from
				}
				if operation != 0 {
					command = fmt.Sprintf(`{"op":"transfer","from":%q,"to":%q,"amount":%d}`, from, to, value)
				}
				accepted := from == "amber" && value <= amber || from == "birch" && value <= birch
				if accepted {
					if from == "amber" {
						amber, birch = amber-value, birch+value
					} else {
						amber, birch = amber+value, birch-value
					}
				}
				if amber < 0 || birch < 0 || amber+birch != 140 {
					t.Fatal("model violated funds invariant")
				}
				status := fmt.Sprintf(`{"amber":%d,"birch":%d}`, amber, birch)
				result := status
				if !accepted {
					result = `{"error":"insufficient_funds"}`
				}
				commands = append(commands, command, `{"op":"balances"}`)
				want = append(want, result, status)
			}
		}
		assertAllImplementations(t, family, commands, want)
	}
}

func TestSourcesVaryPolicyPlacementAndSeedNotState(t *testing.T) {
	for _, family := range []string{"reserving-inventory", "transferring-funds"} {
		structured := application(Options{Family: family, Variant: "structured"})
		scattered := application(Options{Family: family, Variant: "scattered"})
		policy := `return {"error": "insufficient_stock"}`
		if family == "transferring-funds" {
			policy = `return {"error": "insufficient_funds"}`
		}
		if strings.Count(structured, policy) != 1 || strings.Count(scattered, policy) != 2 {
			t.Fatal("policy placement mutation missing")
		}
		if structured == application(Options{Family: family, Variant: "structured", Seed: 1}) {
			t.Fatal("seed did not vary the implementation")
		}
		if strings.Contains(structured, "#") || strings.Contains(scattered, "#") {
			t.Fatal("generated source contains comments")
		}
	}
}

func assertAllImplementations(t *testing.T, family string, commands, want []string) {
	t.Helper()
	for _, variant := range []string{"structured", "scattered"} {
		for _, seed := range []int64{0, 1, -3} {
			t.Run(fmt.Sprintf("%s/%s/%d", family, variant, seed), func(t *testing.T) {
				out := filepath.Join(t.TempDir(), "application")
				if err := Generate(Options{Family: family, Variant: variant, Seed: seed, Out: out}); err != nil {
					t.Fatal(err)
				}
				ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
				defer cancel()
				command := exec.CommandContext(ctx, "python3.12", filepath.Join(out, "application.py"))
				command.Stdin = strings.NewReader(strings.Join(commands, "\n") + "\n")
				var stdout, stderr bytes.Buffer
				command.Stdout, command.Stderr = &stdout, &stderr
				if err := command.Run(); err != nil {
					t.Fatalf("Python process: %v: %s", err, &stderr)
				}
				if stderr.Len() != 0 {
					t.Fatalf("unexpected stderr: %s", &stderr)
				}
				scanner := bufio.NewScanner(&stdout)
				for i, expected := range want {
					if !scanner.Scan() {
						t.Fatalf("missing result %d: %v", i, scanner.Err())
					}
					var actual, expectedObject map[string]any
					if err := json.Unmarshal(scanner.Bytes(), &actual); err != nil {
						t.Fatal(err)
					}
					if err := json.Unmarshal([]byte(expected), &expectedObject); err != nil {
						t.Fatal(err)
					}
					if !reflect.DeepEqual(actual, expectedObject) {
						t.Fatalf("command %d %s: got %v want %v", i, commands[i], actual, expectedObject)
					}
				}
				if scanner.Scan() || scanner.Err() != nil {
					t.Fatalf("extra or unreadable output: %s %v", scanner.Text(), scanner.Err())
				}
			})
		}
	}
}
