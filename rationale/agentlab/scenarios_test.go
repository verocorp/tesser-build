package agentlab_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

type corpusContract struct {
	Version      int               `json:"version"`
	ID           string            `json:"id"`
	Family       string            `json:"family"`
	Requirements []string          `json:"requirements"`
	Vocabulary   map[string]string `json:"vocabulary"`
	Probes       []corpusProbe     `json:"probes"`
	Followups    []corpusFollowup  `json:"followups"`
}

type corpusProbe struct {
	ID       string           `json:"id"`
	Inputs   []map[string]any `json:"inputs"`
	Expected []map[string]any `json:"expected"`
}

type corpusFollowup struct {
	ID           string             `json:"id"`
	Requirements []string           `json:"requirements"`
	Probes       []corpusProbe      `json:"probes"`
	BaseExpected corpusBaseExpected `json:"base_expected,omitempty"`
}

type corpusBaseExpected map[string][]map[string]any

func (expected *corpusBaseExpected) UnmarshalJSON(data []byte) error {
	var values map[string][]map[string]any
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := decoder.Decode(&values); err != nil {
		return err
	}
	if len(values) == 0 {
		return fmt.Errorf("base_expected must be a nonempty object when present")
	}
	*expected = values
	return nil
}

var corpusIDPattern = regexp.MustCompile(`^[a-z][a-z0-9]*(?:-+[a-z0-9]+)*$`)

func TestScenarioCorpusContracts(t *testing.T) {
	files, err := filepath.Glob("scenarios/*.json")
	if err != nil {
		t.Fatal(err)
	}
	families := map[string]string{
		"crud-invariants":                 "reserving-inventory",
		"multi-aggregate-atomic-transfer": "transferring-funds",
		"compensation":                    "compensating-booking",
		"approval-timeout":                "expiring-approval",
		"fanout":                          "joining-fanout",
		"queue-dedup":                     "deduplicating-queue",
		"event-projection":                "projecting-events",
		"actor-state":                     "serializing-actors",
		"streaming-cancellation":          "cancelling-stream",
		"game-tick":                       "advancing-game",
		"vendor-translation":              "translating-vendors",
		"llm-output-policy":               "constraining-llm-output",
	}
	if len(files) != len(families) {
		t.Fatalf("got %d scenarios, want %d distinct families", len(files), len(families))
	}
	ids := map[string]bool{}
	seenFamilies := map[string]bool{}
	for _, file := range files {
		t.Run(filepath.Base(file), func(t *testing.T) {
			data, err := os.ReadFile(file)
			if err != nil {
				t.Fatal(err)
			}
			contract, err := decodeCorpusContract(data)
			if err != nil {
				t.Fatal(err)
			}
			if err := validateCorpusContract(contract, ids); err != nil {
				t.Fatal(err)
			}
			if filepath.Base(file) != contract.ID+".json" {
				t.Errorf("filename does not match scenario ID %q", contract.ID)
			}
			if families[contract.Family] != contract.ID || seenFamilies[contract.Family] {
				t.Errorf("unexpected or duplicate family %q for %q", contract.Family, contract.ID)
			}
			seenFamilies[contract.Family] = true
		})
	}
}

func decodeCorpusContract(data []byte) (corpusContract, error) {
	var contract corpusContract
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := validateCorpusJSONValue(decoder); err != nil {
		return contract, err
	}
	if _, err := decoder.Token(); err != io.EOF {
		return contract, fmt.Errorf("expected exactly one JSON document: %v", err)
	}
	decoder = json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&contract); err != nil {
		return contract, err
	}
	return contract, nil
}

func validateCorpusJSONValue(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return err
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	keys := map[string]bool{}
	for decoder.More() {
		if delimiter == '{' {
			keyToken, err := decoder.Token()
			if err != nil {
				return err
			}
			key, ok := keyToken.(string)
			if !ok || keys[key] {
				return fmt.Errorf("duplicate or invalid JSON key %v", keyToken)
			}
			keys[key] = true
		}
		if err := validateCorpusJSONValue(decoder); err != nil {
			return err
		}
	}
	_, err = decoder.Token()
	return err
}

func validateCorpusContract(contract corpusContract, ids map[string]bool) error {
	if contract.Version != 1 {
		return fmt.Errorf("unsupported version %d", contract.Version)
	}
	if err := claimCorpusID(contract.ID, ids); err != nil {
		return err
	}
	if !corpusIDPattern.MatchString(contract.Family) {
		return fmt.Errorf("invalid family %q", contract.Family)
	}
	if err := validateCorpusRequirements(contract.Requirements); err != nil {
		return err
	}
	if len(contract.Vocabulary) == 0 {
		return fmt.Errorf("empty vocabulary")
	}
	for term, meaning := range contract.Vocabulary {
		if strings.TrimSpace(term) == "" || strings.TrimSpace(meaning) == "" {
			return fmt.Errorf("empty vocabulary term or meaning")
		}
	}
	if len(contract.Probes) < 5 || len(contract.Followups) < 2 {
		return fmt.Errorf("need at least five base probes and two followups")
	}
	seenInputs, err := validateCorpusProbes(contract.Probes, ids)
	if err != nil {
		return err
	}
	baseRequirements := map[string]bool{}
	baseProbes := map[string]corpusProbe{}
	for _, probe := range contract.Probes {
		baseProbes[probe.ID] = probe
	}
	for _, requirement := range contract.Requirements {
		baseRequirements[strings.TrimSpace(requirement)] = true
	}
	followupRequirements := map[string]bool{}
	for _, followup := range contract.Followups {
		if err := claimCorpusID(followup.ID, ids); err != nil {
			return err
		}
		if err := validateCorpusRequirements(followup.Requirements); err != nil {
			return err
		}
		if followup.BaseExpected != nil && len(followup.BaseExpected) == 0 {
			return fmt.Errorf("base_expected must be nonempty when present")
		}
		for id, expected := range followup.BaseExpected {
			base, ok := baseProbes[id]
			if !ok {
				return fmt.Errorf("override %q does not name a base probe", id)
			}
			if len(expected) != len(base.Inputs) {
				return fmt.Errorf("override %q has mismatched input/output cardinality", id)
			}
			for _, output := range expected {
				if len(output) == 0 {
					return fmt.Errorf("override %q has null or empty output object", id)
				}
			}
		}
		for _, requirement := range followup.Requirements {
			requirement = strings.TrimSpace(requirement)
			if baseRequirements[requirement] || followupRequirements[requirement] {
				return fmt.Errorf("followup repeats a base or another followup requirement")
			}
			followupRequirements[requirement] = true
		}
		if len(followup.Probes) < 2 {
			return fmt.Errorf("followup %q needs at least two probes", followup.ID)
		}
		inputs, err := validateCorpusProbes(followup.Probes, ids)
		if err != nil {
			return err
		}
		for signature := range inputs {
			if seenInputs[signature] {
				return fmt.Errorf("followup %q reuses a base or another followup input sequence", followup.ID)
			}
			seenInputs[signature] = true
		}
	}
	return nil
}

func claimCorpusID(id string, ids map[string]bool) error {
	if !corpusIDPattern.MatchString(id) || ids[id] {
		return fmt.Errorf("invalid or duplicate ID %q", id)
	}
	ids[id] = true
	return nil
}

func validateCorpusRequirements(requirements []string) error {
	if len(requirements) == 0 {
		return fmt.Errorf("empty requirements")
	}
	seen := map[string]bool{}
	for _, requirement := range requirements {
		requirement = strings.TrimSpace(requirement)
		if requirement == "" || seen[requirement] {
			return fmt.Errorf("empty or duplicate requirement")
		}
		seen[requirement] = true
	}
	return nil
}

func validateCorpusProbes(probes []corpusProbe, ids map[string]bool) (map[string]bool, error) {
	sequences := map[string]bool{}
	for _, probe := range probes {
		if err := claimCorpusID(probe.ID, ids); err != nil {
			return nil, err
		}
		if len(probe.Inputs) == 0 || len(probe.Inputs) != len(probe.Expected) {
			return nil, fmt.Errorf("probe %q has empty or mismatched input/output cardinality", probe.ID)
		}
		for index, input := range probe.Inputs {
			if input == nil || len(probe.Expected[index]) == 0 {
				return nil, fmt.Errorf("probe %q has null input or empty output object", probe.ID)
			}
		}
		encoded, err := json.Marshal(probe.Inputs)
		if err != nil {
			return nil, err
		}
		if sequences[string(encoded)] {
			return nil, fmt.Errorf("duplicate input sequence in probe %q", probe.ID)
		}
		sequences[string(encoded)] = true
	}
	return sequences, nil
}

func TestCorpusValidatorRejectsMalformedContracts(t *testing.T) {
	data, err := os.ReadFile("scenarios/reserving-inventory.json")
	if err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name   string
		mutate func(*corpusContract)
	}{
		{"wrong-version", func(c *corpusContract) { c.Version = 2 }},
		{"missing-id", func(c *corpusContract) { c.ID = "" }},
		{"missing-family", func(c *corpusContract) { c.Family = "" }},
		{"empty-requirements", func(c *corpusContract) { c.Requirements = nil }},
		{"blank-requirement", func(c *corpusContract) { c.Requirements[0] = " " }},
		{"duplicate-requirement", func(c *corpusContract) { c.Requirements[1] = c.Requirements[0] }},
		{"empty-vocabulary", func(c *corpusContract) { c.Vocabulary = nil }},
		{"blank-meaning", func(c *corpusContract) { c.Vocabulary["stock"] = " " }},
		{"too-few-base-probes", func(c *corpusContract) { c.Probes = c.Probes[:4] }},
		{"too-few-followups", func(c *corpusContract) { c.Followups = c.Followups[:1] }},
		{"too-few-followup-probes", func(c *corpusContract) { c.Followups[0].Probes = c.Followups[0].Probes[:1] }},
		{"empty-followup-requirements", func(c *corpusContract) { c.Followups[0].Requirements = nil }},
		{"empty-base-override", func(c *corpusContract) { c.Followups[0].BaseExpected = corpusBaseExpected{} }},
		{"unknown-base-override", func(c *corpusContract) {
			c.Followups[0].BaseExpected = corpusBaseExpected{"missing": c.Probes[0].Expected}
		}},
		{"followup-is-not-base-override", func(c *corpusContract) {
			c.Followups[0].BaseExpected = corpusBaseExpected{c.Followups[0].Probes[0].ID: c.Followups[0].Probes[0].Expected}
		}},
		{"override-cardinality", func(c *corpusContract) {
			c.Followups[0].BaseExpected = corpusBaseExpected{c.Probes[1].ID: c.Probes[1].Expected[:1]}
		}},
		{"null-override-response", func(c *corpusContract) {
			c.Followups[0].BaseExpected = corpusBaseExpected{c.Probes[0].ID: {nil}}
		}},
		{"duplicate-probe-id", func(c *corpusContract) { c.Probes[1].ID = c.Probes[0].ID }},
		{"duplicate-followup-id", func(c *corpusContract) { c.Followups[1].ID = c.Followups[0].ID }},
		{"cross-tier-id", func(c *corpusContract) { c.Followups[0].Probes[0].ID = c.Probes[0].ID }},
		{"empty-probe", func(c *corpusContract) { c.Probes[0].Inputs = nil; c.Probes[0].Expected = nil }},
		{"cardinality", func(c *corpusContract) { c.Probes[1].Expected = c.Probes[1].Expected[:1] }},
		{"null-input", func(c *corpusContract) { c.Probes[0].Inputs[0] = nil }},
		{"null-output", func(c *corpusContract) { c.Probes[0].Expected[0] = nil }},
		{"duplicate-input-sequence", func(c *corpusContract) {
			c.Probes[1].Inputs = c.Probes[0].Inputs
			c.Probes[1].Expected = c.Probes[0].Expected
		}},
		{"base-input-leaked-to-followup", func(c *corpusContract) {
			c.Followups[0].Probes[0].Inputs = c.Probes[0].Inputs
			c.Followups[0].Probes[0].Expected = c.Probes[0].Expected
		}},
		{"followup-input-reused", func(c *corpusContract) {
			c.Followups[1].Probes[0].Inputs = c.Followups[0].Probes[0].Inputs
			c.Followups[1].Probes[0].Expected = c.Followups[0].Probes[0].Expected
		}},
		{"base-requirement-reused", func(c *corpusContract) { c.Followups[0].Requirements = c.Requirements[:1] }},
		{"followup-requirement-reused", func(c *corpusContract) { c.Followups[1].Requirements = c.Followups[0].Requirements }},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			contract, err := decodeCorpusContract(data)
			if err != nil {
				t.Fatal(err)
			}
			test.mutate(&contract)
			if err := validateCorpusContract(contract, map[string]bool{}); err == nil {
				t.Fatal("malformed contract was accepted")
			}
		})
	}
}

func TestCorpusDecoderRejectsAmbiguousJSON(t *testing.T) {
	for _, data := range []string{
		`{"version":1,"version":1}`,
		`{"vocabulary":{"unit":"first","unit":"second"}}`,
		`{"probes":[{"inputs":[{"op":"read","op":"write"}]}]}`,
		`{"version":1,"unknown":true}`,
		`{"probes":[{"unknown":true}]}`,
		`{"followups":[{"unknown":true}]}`,
		`{"followups":[{"base_expected":null}]}`,
		`{"followups":[{"base_expected":{}}]}`,
		`{"followups":[{"base_expected":{"base":["text"]}}]}`,
		`{"followups":[{"base_expected":{"base":[[]]}}]}`,
		`{"followups":[{"base_expected":{"base":[{}],"base":[{}]}}]}`,
		`{"version":1} {"version":1}`,
		`{"version":1.5}`,
		`{"probes":[{"inputs":[[]]}]}`,
		`{"probes":[{"expected":["text"]}]}`,
		`{"version":`,
	} {
		t.Run(data, func(t *testing.T) {
			if _, err := decodeCorpusContract([]byte(data)); err == nil {
				t.Fatal("ambiguous or malformed JSON was accepted")
			}
		})
	}
}

func TestCorpusDecoderAllowsInvalidDomainNumbers(t *testing.T) {
	data, err := os.ReadFile("scenarios/reserving-inventory.json")
	if err != nil {
		t.Fatal(err)
	}
	contract, err := decodeCorpusContract(data)
	if err != nil {
		t.Fatal(err)
	}
	contract.Probes[0].Inputs[0] = map[string]any{"op": "reserve", "quantity": json.Number("1.5")}
	contract.Probes[0].Expected[0] = map[string]any{"error": "invalid_input"}
	encoded, err := json.Marshal(contract)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := decodeCorpusContract(encoded)
	if err != nil {
		t.Fatal(err)
	}
	if err := validateCorpusContract(decoded, map[string]bool{}); err != nil {
		t.Fatal(err)
	}
}

func TestProducerContractSemanticTraces(t *testing.T) {
	for _, id := range []string{"reserving-inventory", "transferring-funds"} {
		data, err := os.ReadFile(filepath.Join("scenarios", id+".json"))
		if err != nil {
			t.Fatal(err)
		}
		contract, err := decodeCorpusContract(data)
		if err != nil {
			t.Fatal(err)
		}
		policies := append([]corpusFollowup{{ID: "base"}}, contract.Followups...)
		for _, policy := range policies {
			probes := append([]corpusProbe{}, contract.Probes...)
			for index := range probes {
				if expected, ok := policy.BaseExpected[probes[index].ID]; ok {
					probes[index].Expected = expected
				}
			}
			probes = append(probes, policy.Probes...)
			for _, probe := range probes {
				t.Run(policy.ID+"/"+probe.ID, func(t *testing.T) {
					var actual []map[string]any
					if id == "reserving-inventory" {
						actual = traceCorpusInventory(probe.Inputs, strings.TrimPrefix(policy.ID, id+"--"))
					} else {
						actual = traceCorpusFunds(probe.Inputs, strings.TrimPrefix(policy.ID, id+"--"))
					}
					for index := range probe.Inputs {
						got, err := json.Marshal(actual[index])
						if err != nil {
							t.Fatal(err)
						}
						want, err := json.Marshal(probe.Expected[index])
						if err != nil {
							t.Fatal(err)
						}
						if !bytes.Equal(got, want) {
							t.Errorf("line %d: traced %s, declared %s", index+1, got, want)
						}
					}
				})
			}
		}
	}
}

func corpusInteger(input map[string]any, key string, minimum, maximum int) (int, bool) {
	number, ok := input[key].(json.Number)
	if !ok {
		return 0, false
	}
	value, err := number.Int64()
	if err != nil || value < int64(minimum) || value > int64(maximum) {
		return 0, false
	}
	return int(value), true
}

func traceCorpusInventory(inputs []map[string]any, policy string) []map[string]any {
	stock, reserved := 10, 0
	var outputs []map[string]any
	for _, input := range inputs {
		operation, _ := input["op"].(string)
		failure := ""
		quantity, validQuantity := corpusInteger(input, "quantity", 1, 1000)
		buffer := 0
		if policy == "minimum-available" {
			buffer = 2
		}
		switch operation {
		case "status":
			if len(input) != 1 {
				failure = "invalid_input"
			}
		case "reserve", "ship", "release", "restock":
			if len(input) != 2 || !validQuantity {
				failure = "invalid_input"
				break
			}
			switch operation {
			case "reserve", "ship":
				if stock-reserved-quantity < buffer {
					failure = "insufficient_stock"
				} else if operation == "reserve" {
					reserved += quantity
				} else {
					stock -= quantity
				}
			case "release":
				if quantity > reserved {
					failure = "insufficient_reserved"
				} else {
					reserved -= quantity
				}
			case "restock":
				if policy == "stock-ceiling" && stock+quantity > 12 {
					failure = "capacity_exceeded"
				} else {
					stock += quantity
				}
			}
		default:
			failure = "invalid_input"
		}
		if failure != "" {
			outputs = append(outputs, map[string]any{"error": failure})
		} else {
			outputs = append(outputs, map[string]any{"stock": stock, "reserved": reserved, "available": stock - reserved})
		}
	}
	return outputs
}

func traceCorpusFunds(inputs []map[string]any, policy string) []map[string]any {
	balances := map[string]int{"amber": 100, "birch": 40}
	var outputs []map[string]any
	for _, input := range inputs {
		operation, _ := input["op"].(string)
		failure := ""
		switch operation {
		case "balances":
			if len(input) != 1 {
				failure = "invalid_input"
			}
		case "transfer", "purchase":
			from, to, fields := "amber", "birch", 2
			if operation == "transfer" {
				from, _ = input["from"].(string)
				to, _ = input["to"].(string)
				fields = 4
			}
			failCredit, validFlag := false, true
			if value, exists := input["fail_credit"]; exists && policy == "credit-failure" {
				fields++
				failCredit, validFlag = value.(bool)
			}
			amount, validAmount := corpusInteger(input, "amount", 1, 1000)
			_, validFrom := balances[from]
			_, validTo := balances[to]
			if len(input) != fields || !validFlag || !validAmount || !validFrom || !validTo || from == to {
				failure = "invalid_input"
				break
			}
			fee := 0
			if policy == "flat-fee" {
				fee = 2
			}
			if balances[from] < amount+fee {
				failure = "insufficient_funds"
			} else if failCredit {
				failure = "credit_failed"
			} else {
				balances[from] -= amount + fee
				balances[to] += amount
			}
		default:
			failure = "invalid_input"
		}
		if failure != "" {
			outputs = append(outputs, map[string]any{"error": failure})
		} else {
			outputs = append(outputs, map[string]any{"amber": balances["amber"], "birch": balances["birch"]})
		}
	}
	return outputs
}
