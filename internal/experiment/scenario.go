package experiment

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"
)

const maxJSONBytes = 4 << 20

type probe struct {
	ID       string            `json:"id"`
	Inputs   []json.RawMessage `json:"inputs"`
	Expected []json.RawMessage `json:"expected"`
}

type followup struct {
	ID           string                       `json:"id"`
	Requirements []string                     `json:"requirements"`
	Probes       []probe                      `json:"probes"`
	BaseExpected map[string][]json.RawMessage `json:"base_expected,omitempty"`
}

type contract struct {
	Version      int               `json:"version"`
	ID           string            `json:"id"`
	Family       string            `json:"family"`
	Requirements []string          `json:"requirements"`
	Vocabulary   map[string]string `json:"vocabulary"`
	Probes       []probe           `json:"probes"`
	Followups    []followup        `json:"followups"`
}

type Scenario struct {
	contract contract
	digest   string
}

type Brief struct {
	Version      int               `json:"version"`
	ID           string            `json:"id"`
	Family       string            `json:"family"`
	Followup     string            `json:"followup,omitempty"`
	Requirements []string          `json:"requirements"`
	Vocabulary   map[string]string `json:"vocabulary"`
	Protocol     string            `json:"protocol"`
	Safety       string            `json:"safety"`
}

const SafetyNotice = "Not a hostile-code sandbox: candidate processes have same-user access. Run only on disposable cloud machines without secrets. Keep the scenario oracle outside the candidate tree."

func LoadScenario(path string) (Scenario, error) {
	info, err := os.Stat(path)
	if err != nil {
		return Scenario{}, fmt.Errorf("stat scenario: %w", err)
	}
	if !info.Mode().IsRegular() {
		return Scenario{}, fmt.Errorf("scenario must be a regular JSON file")
	}
	file, err := os.Open(path)
	if err != nil {
		return Scenario{}, fmt.Errorf("open scenario: %w", err)
	}
	defer file.Close()
	data, err := io.ReadAll(io.LimitReader(file, maxJSONBytes+1))
	if err != nil {
		return Scenario{}, fmt.Errorf("read scenario: %w", err)
	}
	if len(data) > maxJSONBytes {
		return Scenario{}, fmt.Errorf("scenario exceeds %d bytes", maxJSONBytes)
	}
	object, err := jsonObject(data)
	if err != nil {
		return Scenario{}, fmt.Errorf("scenario: %w", err)
	}
	if err := validateSchema(object); err != nil {
		return Scenario{}, err
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	var value contract
	if err := decoder.Decode(&value); err != nil {
		return Scenario{}, fmt.Errorf("scenario schema: %w", err)
	}
	if err := value.validate(); err != nil {
		return Scenario{}, err
	}
	digest := sha256.Sum256(data)
	return Scenario{contract: value, digest: hex.EncodeToString(digest[:])}, nil
}

func (c contract) validate() error {
	if c.Version != 1 || strings.TrimSpace(c.ID) == "" || strings.TrimSpace(c.Family) == "" {
		return fmt.Errorf("scenario requires version 1, a nonempty id, and a nonempty family")
	}
	if !validRequirements(c.Requirements) || c.Vocabulary == nil || c.Followups == nil {
		return fmt.Errorf("scenario requires nonempty requirements, vocabulary object, and followups array")
	}
	for term, meaning := range c.Vocabulary {
		if strings.TrimSpace(term) == "" || strings.TrimSpace(meaning) == "" {
			return fmt.Errorf("vocabulary terms and meanings must be nonempty")
		}
	}
	ids := map[string]bool{}
	if err := validateProbes(c.Probes, ids); err != nil {
		return err
	}
	followupIDs := map[string]bool{}
	for _, change := range c.Followups {
		if strings.TrimSpace(change.ID) == "" || followupIDs[change.ID] || !validRequirements(change.Requirements) {
			return fmt.Errorf("followups require unique nonempty ids and nonempty requirements")
		}
		followupIDs[change.ID] = true
		for id, expected := range change.BaseExpected {
			found := false
			for _, base := range c.Probes {
				if base.ID == id {
					found = true
					if len(expected) != len(base.Inputs) {
						return fmt.Errorf("base_expected %q must preserve the base input cardinality", id)
					}
				}
			}
			if !found {
				return fmt.Errorf("base_expected %q does not identify a base probe", id)
			}
			for _, message := range expected {
				if _, err := jsonObject(message); err != nil {
					return fmt.Errorf("base_expected %q: %w", id, err)
				}
			}
		}
		if err := validateProbes(change.Probes, ids); err != nil {
			return err
		}
	}
	return nil
}

func validRequirements(requirements []string) bool {
	if len(requirements) == 0 {
		return false
	}
	for _, requirement := range requirements {
		if strings.TrimSpace(requirement) == "" {
			return false
		}
	}
	return true
}

func validateProbes(probes []probe, ids map[string]bool) error {
	if len(probes) == 0 {
		return fmt.Errorf("each scenario and followup requires at least one probe")
	}
	for _, p := range probes {
		if strings.TrimSpace(p.ID) == "" || ids[p.ID] {
			return fmt.Errorf("probe ids must be nonempty and globally unique")
		}
		ids[p.ID] = true
		if len(p.Inputs) == 0 || len(p.Inputs) != len(p.Expected) {
			return fmt.Errorf("probe %q requires matching nonempty inputs and expected responses", p.ID)
		}
		for _, messages := range [][]json.RawMessage{p.Inputs, p.Expected} {
			for _, message := range messages {
				if _, err := jsonObject(message); err != nil {
					return fmt.Errorf("probe %q: %w", p.ID, err)
				}
			}
		}
	}
	return nil
}

func (s Scenario) selected(followupID string) ([]probe, []string, error) {
	if err := s.contract.validate(); err != nil {
		return nil, nil, err
	}
	probes := append([]probe(nil), s.contract.Probes...)
	requirements := append([]string(nil), s.contract.Requirements...)
	if followupID == "" {
		return probes, requirements, nil
	}
	for _, change := range s.contract.Followups {
		if change.ID == followupID {
			for index, base := range probes {
				if expected, exists := change.BaseExpected[base.ID]; exists {
					probes[index].Expected = expected
				}
			}
			return append(probes, change.Probes...), append(requirements, change.Requirements...), nil
		}
	}
	return nil, nil, fmt.Errorf("unknown followup %q", followupID)
}

func (s Scenario) Brief(followupID string) (Brief, error) {
	_, requirements, err := s.selected(followupID)
	if err != nil {
		return Brief{}, err
	}
	vocabulary := make(map[string]string, len(s.contract.Vocabulary))
	for term, meaning := range s.contract.Vocabulary {
		vocabulary[term] = meaning
	}
	return Brief{
		Version: s.contract.Version, ID: s.contract.ID, Family: s.contract.Family,
		Followup: followupID, Requirements: requirements, Vocabulary: vocabulary,
		Protocol: "Read one JSON object per stdin line until EOF; emit exactly one JSON object per input line, in order, with no other stdout. JSON object key order and equivalent number representations do not matter; arrays remain ordered. Exit zero. Each probe starts a fresh process in the same copied candidate tree. Gates and probes must not modify that tree. Followup verification also reruns all base probes.",
		Safety:   SafetyNotice,
	}, nil
}

func jsonObject(data []byte) (map[string]any, error) {
	if !utf8.Valid(data) {
		return nil, fmt.Errorf("JSON must be valid UTF-8")
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	value, err := jsonValue(decoder)
	if err != nil {
		return nil, err
	}
	if _, err := decoder.Token(); err != io.EOF {
		return nil, fmt.Errorf("expected exactly one JSON value")
	}
	object, ok := value.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("expected a JSON object")
	}
	return object, nil
}

func validateSchema(object map[string]any) error {
	if !schemaFields(object, "version", "id", "family", "requirements", "vocabulary", "probes", "followups") {
		return fmt.Errorf("scenario fields must match the version 1 schema exactly")
	}
	probeGroups := []any{object["probes"]}
	changes, ok := object["followups"].([]any)
	if !ok {
		return fmt.Errorf("followups must be an array")
	}
	for _, change := range changes {
		fields, ok := change.(map[string]any)
		if !ok {
			return fmt.Errorf("followup fields must match the version 1 schema exactly")
		}
		names := []string{"id", "requirements", "probes"}
		if overrides, exists := fields["base_expected"]; exists {
			names = append(names, "base_expected")
			expected, ok := overrides.(map[string]any)
			if !ok || len(expected) == 0 {
				return fmt.Errorf("supplied base_expected must be a nonempty object")
			}
		}
		if !schemaFields(fields, names...) {
			return fmt.Errorf("followup fields must match the version 1 schema exactly")
		}
		probeGroups = append(probeGroups, fields["probes"])
	}
	for _, group := range probeGroups {
		probes, ok := group.([]any)
		if !ok {
			return fmt.Errorf("probes must be an array")
		}
		for _, p := range probes {
			fields, ok := p.(map[string]any)
			if !ok || !schemaFields(fields, "id", "inputs", "expected") {
				return fmt.Errorf("probe fields must match the version 1 schema exactly")
			}
		}
	}
	return nil
}

func schemaFields(object map[string]any, fields ...string) bool {
	if len(object) != len(fields) {
		return false
	}
	for _, field := range fields {
		if _, exists := object[field]; !exists {
			return false
		}
	}
	return true
}

func jsonValue(decoder *json.Decoder) (any, error) {
	token, err := decoder.Token()
	if err != nil {
		return nil, err
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return token, nil
	}
	switch delimiter {
	case '{':
		object := map[string]any{}
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				return nil, err
			}
			key, ok := keyToken.(string)
			if !ok {
				return nil, fmt.Errorf("invalid object key")
			}
			if _, exists := object[key]; exists {
				return nil, fmt.Errorf("duplicate JSON object key")
			}
			value, err := jsonValue(decoder)
			if err != nil {
				return nil, err
			}
			object[key] = value
		}
		if _, err := decoder.Token(); err != nil {
			return nil, err
		}
		return object, nil
	case '[':
		array := []any{}
		for decoder.More() {
			value, err := jsonValue(decoder)
			if err != nil {
				return nil, err
			}
			array = append(array, value)
		}
		if _, err := decoder.Token(); err != nil {
			return nil, err
		}
		return array, nil
	default:
		return nil, fmt.Errorf("unexpected JSON delimiter")
	}
}
