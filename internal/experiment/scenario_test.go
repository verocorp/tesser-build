package experiment_test

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/verocorp/tesser-build/internal/experiment"
)

func TestScenarioRejectsMalformedContracts(t *testing.T) {
	cases := map[string]string{
		"empty":             "",
		"trailing":          contractJSON + `{}`,
		"wrong-version":     strings.Replace(contractJSON, `"version":1`, `"version":2`, 1),
		"wrong-case":        strings.Replace(contractJSON, `"version":1`, `"Version":1`, 1),
		"missing-field":     strings.Replace(contractJSON, `"version":1,`, "", 1),
		"unknown-field":     strings.Replace(contractJSON, `"version":1`, `"version":1,"extra":true`, 1),
		"duplicate-key":     strings.Replace(contractJSON, `"version":1`, `"version":1,"version":1`, 1),
		"duplicate-probe":   strings.Replace(contractJSON, `"hidden-probe"`, `"base"`, 1),
		"empty-id":          strings.Replace(contractJSON, `"trial"`, `" "`, 1),
		"empty-requirement": strings.Replace(contractJSON, `"Echo the objects."`, `""`, 1),
		"null-requirement":  strings.Replace(contractJSON, `"Echo the objects."`, `null`, 1),
		"null-vocabulary":   strings.Replace(contractJSON, `{"object":"JSON object"}`, `null`, 1),
		"empty-meaning":     strings.Replace(contractJSON, `"JSON object"`, `""`, 1),
		"nonobject":         strings.Replace(contractJSON, `{"x":1}`, `[]`, 1),
		"null-input":        strings.Replace(contractJSON, `{"x":1}`, `null`, 1),
		"duplicate-input":   strings.Replace(contractJSON, `{"x":1}`, `{"x":1,"x":2}`, 1),
		"wrong-count":       strings.Replace(contractJSON, `"expected":[{"x":1},{"x":2}]`, `"expected":[{"x":1}]`, 1),
		"empty-inputs":      strings.Replace(contractJSON, `"inputs":[{"x":1},{"x":2}]`, `"inputs":[]`, 1),
		"empty-probes":      strings.Replace(contractJSON, `[{"id":"base","inputs":[{"x":1},{"x":2}],"expected":[{"x":1},{"x":2}]}]`, `[]`, 1),
		"bad-hidden-probe":  strings.Replace(contractJSON, `"inputs":[{"secret":"private-input"}]`, `"inputs":[]`, 1),
		"invalid-utf8":      strings.Replace(contractJSON, "trial", "\xff", 1),
	}
	for name, data := range cases {
		t.Run(name, func(t *testing.T) {
			options := optionsFor(t, "cat")
			if err := os.WriteFile(options.ScenarioPath, []byte(data), 0600); err != nil {
				t.Fatal(err)
			}
			if _, err := experiment.LoadScenario(options.ScenarioPath); err == nil {
				t.Fatal("malformed contract accepted")
			}
			result := experiment.Verify(context.Background(), options)
			if result.Status != experiment.InfraError || len(result.Stages) != 0 {
				t.Fatalf("malformed contract executed: %+v", result)
			}
		})
	}
}

func TestBriefDoesNotRevealOracleOrUndisclosedFollowup(t *testing.T) {
	options := optionsFor(t, "cat")
	scenario, err := experiment.LoadScenario(options.ScenarioPath)
	if err != nil {
		t.Fatal(err)
	}
	brief, err := scenario.Brief("")
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(brief)
	if err != nil {
		t.Fatal(err)
	}
	for _, hidden := range []string{"secret-change", "hidden-probe", "private-input", "private-answer", "Selected hidden requirement.", `"probes"`, `"expected"`} {
		if strings.Contains(string(data), hidden) {
			t.Fatalf("brief revealed %q: %s", hidden, data)
		}
	}
	if len(brief.Requirements) != 1 || brief.Vocabulary["object"] != "JSON object" || brief.Protocol == "" || !strings.Contains(brief.Safety, "Not a hostile-code sandbox") {
		t.Fatalf("brief missing instructions: %+v", brief)
	}
	brief.Requirements[0] = "mutated"
	brief.Vocabulary["object"] = "mutated"
	selected, err := scenario.Brief("secret-change")
	if err != nil || len(selected.Requirements) != 2 || selected.Requirements[0] != "Echo the objects." || selected.Vocabulary["object"] != "JSON object" {
		t.Fatalf("brief aliasing or selection error: %+v %v", selected, err)
	}
	data, err = json.Marshal(selected)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), "private-answer") || strings.Contains(string(data), "private-input") || strings.Contains(string(data), "hidden-probe") {
		t.Fatalf("selected brief revealed the oracle: %s", data)
	}
	if _, err := scenario.Brief("unknown"); err == nil {
		t.Fatal("unknown followup accepted")
	}
	if _, err := (experiment.Scenario{}).Brief(""); err == nil {
		t.Fatal("zero scenario accepted")
	}
}

func TestExactNestedJSONEquality(t *testing.T) {
	cases := []struct {
		name     string
		expected string
		actual   string
		status   string
	}{
		{"nested-order", `{"a":[1,true,null,{"n":-0}],"b":"x"}`, `{"b":"x","a":[1.0,true,null,{"n":0e999999999999999999999}]}`, experiment.Correct},
		{"large-exact", `{"n":123456789012345678901234567890}`, `{"n":12345678901234567890123456789e1}`, experiment.Correct},
		{"large-distinct", `{"n":9007199254740993}`, `{"n":9007199254740992}`, experiment.Incorrect},
		{"huge-exponent", `{"n":1e1000000000000000000000}`, `{"n":10e999999999999999999999}`, experiment.Correct},
		{"array-order", `{"a":[1,2]}`, `{"a":[2,1]}`, experiment.Incorrect},
		{"missing-null", `{"x":null}`, `{}`, experiment.Incorrect},
		{"type-mismatch", `{"x":1}`, `{"x":"1"}`, experiment.Incorrect},
		{"nested-type", `{"x":true}`, `{"x":[]}`, experiment.Incorrect},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			options := optionsFor(t, "printf '%s\\n' '"+test.actual+"' '"+test.actual+"'")
			data := strings.Replace(contractJSON, `"expected":[{"x":1},{"x":2}]`, `"expected":[`+test.expected+`,`+test.expected+`]`, 1)
			if err := os.WriteFile(options.ScenarioPath, []byte(data), 0600); err != nil {
				t.Fatal(err)
			}
			result := experiment.Verify(context.Background(), options)
			if result.Status != test.status {
				t.Fatalf("wrong comparison: %+v", result)
			}
		})
	}
}

func TestScenarioRejectsDuplicateFollowupIDs(t *testing.T) {
	options := optionsFor(t, "cat")
	var contract map[string]any
	if err := json.Unmarshal([]byte(contractJSON), &contract); err != nil {
		t.Fatal(err)
	}
	followups := contract["followups"].([]any)
	contract["followups"] = append(followups, followups[0])
	data, err := json.Marshal(contract)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(options.ScenarioPath, data, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := experiment.LoadScenario(options.ScenarioPath); err == nil || !strings.Contains(err.Error(), "unique") {
		t.Fatalf("duplicate followup accepted: %v", err)
	}
}

func TestScenarioRejectsInvalidBaseExpectedOverrides(t *testing.T) {
	for name, override := range map[string]string{
		"empty":           `{}`,
		"null":            `null`,
		"unknown-base":    `{"unknown":[{}]}`,
		"followup-probe":  `{"hidden-probe":[{}]}`,
		"wrong-count":     `{"base":[{}]}`,
		"empty-responses": `{"base":[]}`,
		"null-responses":  `{"base":null}`,
		"nonobject":       `{"base":[[],{}]}`,
		"null-object":     `{"base":[null,{}]}`,
		"duplicate-key":   `{"base":[{},{}],"base":[{},{}]}`,
	} {
		t.Run(name, func(t *testing.T) {
			options := optionsFor(t, "cat")
			data := strings.Replace(contractJSON, `"id":"secret-change"`, `"id":"secret-change","base_expected":`+override, 1)
			if err := os.WriteFile(options.ScenarioPath, []byte(data), 0600); err != nil {
				t.Fatal(err)
			}
			if _, err := experiment.LoadScenario(options.ScenarioPath); err == nil {
				t.Fatal("invalid override accepted")
			}
		})
	}
}

func TestFollowupOverridesKeepAllBaseInputsAndStayHidden(t *testing.T) {
	options := optionsFor(t, `while read -r line; do
case "$line" in
  *private-input*) printf '{"secret":"private-answer"}\n';;
  *keep*) printf '{"keep":true}\n';;
  *1*) printf '{"x":10}\n';;
  *2*) printf '{"x":20}\n';;
esac
done`)
	data := strings.Replace(contractJSON, `"id":"secret-change"`, `"id":"secret-change","base_expected":{"base":[{"x":10},{"x":20}]}`, 1)
	data = strings.Replace(data, `"expected":[{"x":1},{"x":2}]}]`, `"expected":[{"x":1},{"x":2}]},{"id":"retained","inputs":[{"keep":true}],"expected":[{"keep":true}]}]`, 1)
	if err := os.WriteFile(options.ScenarioPath, []byte(data), 0600); err != nil {
		t.Fatal(err)
	}
	options.Followup = "secret-change"
	result := experiment.Verify(context.Background(), options)
	if result.Status != experiment.Correct || len(result.Stages) != 3 || result.Stages[0].ID != "base" || result.Stages[0].Responses != 2 || result.Stages[1].ID != "retained" || result.Stages[2].ID != "hidden-probe" {
		t.Fatalf("base input coverage or overrides incorrect: %+v", result)
	}
	options.Followup = ""
	base := experiment.Verify(context.Background(), options)
	if base.Status != experiment.Incorrect || len(base.Stages) != 1 {
		t.Fatalf("followup overrides changed base expectations: %+v", base)
	}
	scenario, err := experiment.LoadScenario(options.ScenarioPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, selected := range []string{"", "secret-change"} {
		brief, err := scenario.Brief(selected)
		if err != nil {
			t.Fatal(err)
		}
		encoded, err := json.Marshal(brief)
		if err != nil {
			t.Fatal(err)
		}
		for _, hidden := range []string{"base_expected", "private-answer", `"x":10`, `"x":20`} {
			if strings.Contains(string(encoded), hidden) {
				t.Fatalf("brief revealed override oracle %q: %s", hidden, encoded)
			}
		}
	}
}
