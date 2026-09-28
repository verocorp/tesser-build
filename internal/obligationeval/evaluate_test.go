package obligationeval

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"
)

func rawJSON(t *testing.T, value interface{}) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func fixture(t *testing.T, name string, value interface{}) {
	t.Helper()
	data, err := os.ReadFile("testdata/" + name + ".json")
	if err != nil {
		t.Fatal(err)
	}
	if err := decode(data, value); err != nil {
		t.Fatal(err)
	}
}

func calibration(t *testing.T) Envelope {
	t.Helper()
	var source Case
	var gold Gold
	var responses []struct {
		Label     string          `json:"label"`
		Candidate json.RawMessage `json:"candidate"`
	}
	var reviews []json.RawMessage
	fixture(t, "case", &source)
	fixture(t, "gold", &gold)
	fixture(t, "responses", &responses)
	fixture(t, "judgments", &reviews)
	if len(responses) != 6 || len(reviews) != 6 {
		t.Fatal("six adopted controls required")
	}
	envelope := Envelope{SchemaVersion: SchemaVersion, Records: []Record{}}
	for i, response := range responses {
		envelope.Records = append(envelope.Records, Record{CandidateLabel: response.Label, Case: source, Gold: gold, CandidateRaw: string(response.Candidate), Review: reviews[i]})
	}
	return envelope
}

func evaluated(t *testing.T, envelope Envelope) Report {
	t.Helper()
	report, err := Evaluate(rawJSON(t, envelope))
	if err != nil {
		t.Fatal(err)
	}
	return report
}

func TestCalibrationFixtures(t *testing.T) {
	envelope := calibration(t)
	report := evaluated(t, envelope)
	full := []int{0, 0, 4, 0, 1, 1}
	partial := []int{0, 0, 0, 1, 0, 0}
	unsupported := []int{0, 4, 0, 1, 0, 0}
	precisionNumerator := []int{0, 0, 5, 1, 1, 1}
	precisionDenominator := []int{0, 4, 5, 2, 1, 1}
	for i, result := range report.Results {
		if result.Status != "scored" || result.Pass == nil || *result.Pass {
			t.Fatalf("control %d: %+v", i+1, result)
		}
		if !result.CandidateFormatValid || result.Grounding.ItemsWithoutValidQuote != 0 || result.Grounding.Numerator != result.Grounding.Denominator {
			t.Fatalf("control %d grounding: %+v", i+1, result.Grounding)
		}
		metrics := result.Metrics
		if metrics.CommitmentRecall.Numerator != full[i] || metrics.CommitmentRecall.Denominator != 4 || metrics.CommitmentRecall.Partial != partial[i] || metrics.CommitmentRecall.Missing != 4-full[i]-partial[i] || metrics.UnsupportedClaims != unsupported[i] {
			t.Fatalf("control %d metrics: %+v", i+1, metrics)
		}
		if metrics.AssertionPrecision.Numerator != precisionNumerator[i] || metrics.AssertionPrecision.Denominator != precisionDenominator[i] {
			t.Fatalf("control %d precision: %+v", i+1, metrics.AssertionPrecision)
		}
		if metrics.AssumptionCoverage.Value != nil || metrics.AssumptionCoverage.Denominator != 0 || metrics.RequiredAmbiguity.Denominator != 1 {
			t.Fatalf("control %d denominators: %+v", i+1, metrics)
		}
	}
	if report.Results[0].Metrics.AssertionPrecision.Value != nil || report.Results[0].Grounding.Value != nil {
		t.Fatal("empty denominators must be N/A")
	}
	if report.Results[1].Metrics.MaterialRoleErrors != 1 {
		t.Fatal("invented reminder promotion must remain visible")
	}
	if report.Results[2].Metrics.OmnibusItems != 1 || report.Results[2].Metrics.NonmaterialRoleMismatches != 1 || report.Results[2].Metrics.RequiredAmbiguity.Numerator != 1 || report.Results[2].Metrics.GoalCoverage.Numerator != 1 {
		t.Fatal("copied request has full semantics but fails usability")
	}
	if report.Results[5].Metrics.Duplicates.Numerator != 1 || report.Results[5].Metrics.Duplicates.Denominator != 2 {
		t.Fatal("duplicate must not add recall or precision")
	}
	if report.BySplit[0].Cases.Failed != 6 || report.BySplit[0].ScoredOnlyMicroCommitmentRecall.Numerator != 6 || report.BySplit[0].ScoredOnlyMicroCommitmentRecall.Denominator != 24 {
		t.Fatalf("aggregate: %+v", report.BySplit)
	}
}

func positive(t *testing.T) Envelope {
	t.Helper()
	record := calibration(t).Records[0]
	record.CandidateLabel = "synthetic_positive"
	value := candidate{CaseID: record.Case.CaseID, Items: []item{}}
	judgment := review{CaseID: record.Case.CaseID, CandidateLabel: record.CandidateLabel, GoldVersion: record.Gold.GoldVersion, ReviewStatus: "complete", References: []referenceJudgment{}, Claims: []claimJudgment{}, Ambiguities: []ambiguityJudgment{}, Flags: []itemFlag{}, Disagreements: []json.RawMessage{}}
	for i, ref := range record.Gold.References {
		if ref.Required != nil && !*ref.Required {
			judgment.References = append(judgment.References, referenceJudgment{ref.ID, []string{}, "missing", "The optional proposal is intentionally omitted.", ref.Evidence})
			continue
		}
		id := fmt.Sprintf("i%d", i)
		value.Items = append(value.Items, item{id, ref.AcceptedKinds[0], ref.Evidence[0], ref.Evidence})
		judgment.References = append(judgment.References, referenceJudgment{ref.ID, []string{id}, "full", "This individual source sentence preserves the complete reference meaning.", ref.Evidence})
		verdict := "supported"
		if ref.Type == "uncertainty" {
			verdict = "open_question"
			judgment.Ambiguities = append(judgment.Ambiguities, ambiguityJudgment{ref.ID, []string{id}, "preserved", "The unresolved decision remains explicitly undecided.", ref.Evidence})
		}
		judgment.Claims = append(judgment.Claims, claimJudgment{fmt.Sprintf("c%d", i), id, ref.Evidence[0], verdict, nil, "This is the complete individual assertion from the source, with its conditions unchanged.", ref.Evidence})
	}
	record.CandidateRaw = string(rawJSON(t, value))
	record.Review = rawJSON(t, judgment)
	return Envelope{SchemaVersion, []Record{record}}
}

func TestCompleteSyntheticPositiveAndPreservedInputs(t *testing.T) {
	envelope := positive(t)
	result := evaluated(t, envelope).Results[0]
	if result.Pass == nil || !*result.Pass || result.Status != "scored" {
		t.Fatalf("synthetic positive: %+v", result)
	}
	if result.Metrics.CommitmentRecall.Numerator != 4 || result.Metrics.GoalCoverage.Numerator != 1 || result.Metrics.RequiredAmbiguity.Numerator != 1 || result.Metrics.AssertionPrecision.Numerator != 5 || result.Metrics.AssertionPrecision.Denominator != 5 {
		t.Fatalf("metrics: %+v", result.Metrics)
	}
	if !reflect.DeepEqual(rawJSON(t, result.Input), rawJSON(t, envelope.Records[0])) {
		t.Fatal("input fields, conditions, accepted kinds, notes, raw text and judgments must survive")
	}
	first := rawJSON(t, evaluated(t, envelope))
	second := rawJSON(t, evaluated(t, envelope))
	if string(first) != string(second) {
		t.Fatal("replay must be deterministic")
	}
}

func alteredReview(t *testing.T, envelope *Envelope, change func(*review)) {
	t.Helper()
	var judgment review
	if err := decode(envelope.Records[0].Review, &judgment); err != nil {
		t.Fatal(err)
	}
	change(&judgment)
	envelope.Records[0].Review = rawJSON(t, judgment)
}

func alteredCandidate(t *testing.T, envelope *Envelope, change func(*candidate)) {
	t.Helper()
	var value candidate
	if err := decode([]byte(envelope.Records[0].CandidateRaw), &value); err != nil {
		t.Fatal(err)
	}
	change(&value)
	envelope.Records[0].CandidateRaw = string(rawJSON(t, value))
}

func TestInvalidReviewsAreUnscorable(t *testing.T) {
	tests := []struct {
		name   string
		change func(*review)
	}{
		{"status", func(r *review) { r.ReviewStatus = "approved" }},
		{"unresolved", func(r *review) { r.ReviewStatus = "needs_adjudication" }},
		{"disagreement", func(r *review) { r.Disagreements = []json.RawMessage{json.RawMessage(`"unresolved coverage"`)} }},
		{"case", func(r *review) { r.CaseID = "D02" }},
		{"candidate", func(r *review) { r.CandidateLabel = "other" }},
		{"version", func(r *review) { r.GoldVersion = "stale" }},
		{"reference_enum", func(r *review) { r.References[0].Coverage = "mostly" }},
		{"missing_reference", func(r *review) { r.References = r.References[1:] }},
		{"duplicate_reference", func(r *review) { r.References = append(r.References, r.References[0]) }},
		{"foreign_reference", func(r *review) { r.References[0].ReferenceID = "D02-G1" }},
		{"unknown_item", func(r *review) { r.References[0].ItemIDs = []string{"other"} }},
		{"repeated_item", func(r *review) { r.References[0].ItemIDs = append(r.References[0].ItemIDs, r.References[0].ItemIDs[0]) }},
		{"empty_full", func(r *review) { r.References[0].ItemIDs = []string{} }},
		{"empty_partial", func(r *review) { r.References[0].Coverage = "partial"; r.References[0].ItemIDs = []string{} }},
		{"claim_enum", func(r *review) { r.Claims[0].Verdict = "true" }},
		{"duplicate_claim", func(r *review) { r.Claims = append(r.Claims, r.Claims[0]) }},
		{"invalid_claim_id", func(r *review) { r.Claims[0].ClaimID = "not an id" }},
		{"fragment", func(r *review) { r.Claims[0].CandidateFragment = "not in the candidate" }},
		{"empty_fragment", func(r *review) { r.Claims[0].CandidateFragment = "" }},
		{"forward_duplicate", func(r *review) { id := r.Claims[1].ClaimID; r.Claims[0].DuplicateOf = &id }},
		{"self_duplicate", func(r *review) { id := r.Claims[0].ClaimID; r.Claims[0].DuplicateOf = &id }},
		{"unknown_duplicate", func(r *review) { id := "missing"; r.Claims[0].DuplicateOf = &id }},
		{"unaccounted_item", func(r *review) { r.Claims = r.Claims[1:] }},
		{"empty_rationale", func(r *review) { r.Claims[0].Rationale = " " }},
		{"invalid_quote", func(r *review) { r.Claims[0].SourceQuotes = []string{"not in source"} }},
		{"no_quotes", func(r *review) { r.Claims[0].SourceQuotes = []string{} }},
		{"empty_quote", func(r *review) { r.Claims[0].SourceQuotes = []string{""} }},
		{"missing_required_ambiguity", func(r *review) { r.Ambiguities = []ambiguityJudgment{} }},
		{"ambiguity_enum", func(r *review) { r.Ambiguities[0].Status = "full" }},
		{"ambiguity_wrong_reference", func(r *review) { r.Ambiguities[0].ReferenceID = "D01-G1" }},
		{"duplicate_ambiguity", func(r *review) { r.Ambiguities = append(r.Ambiguities, r.Ambiguities[0]) }},
		{"preserved_without_item", func(r *review) { r.Ambiguities[0].ItemIDs = []string{} }},
		{"invalid_flag", func(r *review) {
			r.Flags = []itemFlag{{"i0", "nonmaterial_role_error", "Wrong flag spelling", r.Claims[0].SourceQuotes}}
		}},
		{"duplicate_flag", func(r *review) {
			f := itemFlag{"i0", "omnibus", "Repeated flag", r.Claims[0].SourceQuotes}
			r.Flags = []itemFlag{f, f}
		}},
		{"unknown_flag_item", func(r *review) { r.Flags = []itemFlag{{"unknown", "omnibus", "Bad target", r.Claims[0].SourceQuotes}} }},
		{"over_budget", func(r *review) {
			for len(r.Claims) < 101 {
				r.Claims = append(r.Claims, r.Claims[0])
			}
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			envelope := positive(t)
			alteredReview(t, &envelope, test.change)
			result := evaluated(t, envelope).Results[0]
			if result.Status != "unscorable" || result.Pass != nil || result.Metrics != nil || len(result.Reasons) == 0 {
				t.Fatalf("%+v", result)
			}
		})
	}
}

func TestCandidateFailuresAndBudget(t *testing.T) {
	tests := []struct {
		name   string
		change func(*candidate)
	}{
		{"case", func(c *candidate) { c.CaseID = "D02" }},
		{"id", func(c *candidate) { c.Items[0].ID = "bad id" }},
		{"duplicate", func(c *candidate) { c.Items = append(c.Items, c.Items[0]) }},
		{"kind", func(c *candidate) { c.Items[0].Kind = "requirement" }},
		{"text", func(c *candidate) { c.Items[0].Text = " " }},
		{"empty_quote", func(c *candidate) { c.Items[0].Evidence = []string{""} }},
		{"invalid_quote", func(c *candidate) { c.Items[0].Evidence = []string{"unquoted"} }},
		{"no_quotes", func(c *candidate) { c.Items[0].Evidence = []string{} }},
		{"mixed_quotes", func(c *candidate) { c.Items[0].Evidence = append(c.Items[0].Evidence, "unquoted") }},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			envelope := positive(t)
			alteredCandidate(t, &envelope, test.change)
			result := evaluated(t, envelope).Results[0]
			if result.Status != "candidate_failure" || result.Pass != nil || result.Metrics != nil {
				t.Fatalf("%+v", result)
			}
		})
	}
	envelope := positive(t)
	alteredCandidate(t, &envelope, func(c *candidate) {
		for len(c.Items) < 41 {
			row := c.Items[0]
			row.ID = fmt.Sprintf("extra%d", len(c.Items))
			c.Items = append(c.Items, row)
		}
	})
	result := evaluated(t, envelope).Results[0]
	if result.Status != "unscorable" || result.Pass != nil {
		t.Fatalf("%+v", result)
	}
}

func TestStrictJSONBoundaries(t *testing.T) {
	for _, raw := range []string{`{`, `null`, `{"case_id":"D01"}`, `{"case_id":"D01","items":null}`, `{"case_id":"D01","items":[],"unknown":true}`, `{"case_id":"D01","items":[],"items":[]}`, `{"Case_ID":"D01","items":[]}`, `{"case_id":"D01","items":[{"id":"i1","kind":"goal","text":"x"}]}`, `{"case_id":"D01","items":[]} {}`} {
		envelope := positive(t)
		envelope.Records[0].CandidateRaw = raw
		result := evaluated(t, envelope).Results[0]
		if result.Status != "candidate_failure" || result.Input.CandidateRaw != raw {
			t.Fatalf("candidate %q: %+v", raw, result)
		}
	}
	for _, raw := range []string{`null`, `{}`, `{"unknown":true}`, `{"case_id":"D01","case_id":"D01"}`} {
		envelope := positive(t)
		envelope.Records[0].Review = json.RawMessage(raw)
		result := evaluated(t, envelope).Results[0]
		if result.Status != "unscorable" {
			t.Fatalf("review %s: %+v", raw, result)
		}
	}
	valid := string(rawJSON(t, positive(t)))
	for _, raw := range []string{`{}`, `null`, `{"schema_version":"obligations-eval-v1","records":[]}`, `{"schema_version":"obligations-eval-v1","records":null}`, strings.Replace(valid, `"schema_version":`, `"unknown":0,"schema_version":`, 1), strings.Replace(valid, `"split":"development"`, `"split":"unknown"`, 1), strings.Replace(valid, `"required":false`, `"required":null`, 1), strings.Replace(valid, `"condition":null`, `"condition":12`, 1), strings.Replace(valid, `"review_notes":`, `"unknown":0,"review_notes":`, 1), valid + ` {}`} {
		if _, err := Evaluate([]byte(raw)); err == nil {
			t.Fatalf("expected input error: %s", raw)
		}
	}
}

func TestInvalidGoldAndPairs(t *testing.T) {
	tests := []struct {
		name   string
		change func(*Envelope)
	}{
		{"version", func(e *Envelope) { e.SchemaVersion = "v2" }},
		{"pair", func(e *Envelope) { e.Records = append(e.Records, e.Records[0]) }},
		{"case", func(e *Envelope) { e.Records[0].Gold.CaseID = "D02" }},
		{"id", func(e *Envelope) { e.Records[0].Gold.References[0].ID = "G1" }},
		{"duplicate", func(e *Envelope) { g := &e.Records[0].Gold; g.References = append(g.References, g.References[0]) }},
		{"enum", func(e *Envelope) { e.Records[0].Gold.References[0].Type = "requirement" }},
		{"kind", func(e *Envelope) { e.Records[0].Gold.References[0].AcceptedKinds = []string{"unknown"} }},
		{"empty_kinds", func(e *Envelope) { e.Records[0].Gold.References[0].AcceptedKinds = []string{} }},
		{"repeated_kind", func(e *Envelope) { e.Records[0].Gold.References[0].AcceptedKinds = []string{"goal", "goal"} }},
		{"quote", func(e *Envelope) { e.Records[0].Gold.References[0].Evidence = []string{"absent"} }},
		{"text", func(e *Envelope) { e.Records[0].Gold.References[0].Text = "" }},
		{"required_wrong_type", func(e *Envelope) { b := false; e.Records[0].Gold.References[0].Required = &b }},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			e := positive(t)
			test.change(&e)
			if _, err := Evaluate(rawJSON(t, e)); err == nil {
				t.Fatal("expected input error")
			}
		})
	}
}

func TestDiagnosticSemanticsAreRecordedNotInferred(t *testing.T) {
	envelope := positive(t)
	alteredReview(t, &envelope, func(r *review) {
		r.Claims[0].Verdict = "contradicted"
		r.Claims[1].Verdict = "unsupported"
		id := r.Claims[0].ClaimID
		r.Claims[1].DuplicateOf = &id
		r.Ambiguities[0].Status = "resolved_without_authority"
	})
	result := evaluated(t, envelope).Results[0]
	if result.Status != "scored" || *result.Pass || result.Metrics.ContradictedClaims != 1 || result.Metrics.UnsupportedClaims != 1 || result.Metrics.AssertionPrecision.Numerator != 3 || result.Metrics.AssertionPrecision.Denominator != 4 || result.Metrics.Duplicates.Numerator != 1 || result.Metrics.RequiredAmbiguity.Numerator != 0 {
		t.Fatalf("%+v", result)
	}
	envelope = positive(t)
	alteredReview(t, &envelope, func(r *review) {
		id := r.Claims[0].ClaimID
		claim := r.Claims[0]
		claim.ClaimID = "extra"
		claim.DuplicateOf = &id
		r.Claims = append(r.Claims, claim)
	})
	result = evaluated(t, envelope).Results[0]
	if !*result.Pass || result.Metrics.Duplicates.Numerator != 1 || result.Metrics.AssertionPrecision.Denominator != 5 {
		t.Fatal("harmless duplication alone must not fail")
	}
	envelope = positive(t)
	envelope.Records[0].Gold.References[0].AcceptedKinds = []string{"question"}
	result = evaluated(t, envelope).Results[0]
	if !*result.Pass {
		t.Fatal("accepted kinds are context for reviewers, not automated semantic rejection")
	}
}

func TestNAOptionalAmbiguityAndSourceAssumptions(t *testing.T) {
	envelope := positive(t)
	for i := range envelope.Records[0].Gold.References {
		if envelope.Records[0].Gold.References[i].Type == "commitment" {
			envelope.Records[0].Gold.References[i].Type = "assumption"
		}
	}
	result := evaluated(t, envelope).Results[0]
	if !*result.Pass || result.Metrics.CommitmentRecall.Value != nil || result.Metrics.AssumptionCoverage.Numerator != 4 || result.Metrics.AssumptionCoverage.Denominator != 4 {
		t.Fatalf("%+v", result.Metrics)
	}
	report := evaluated(t, envelope)
	if report.ByCandidate[0].ScoredOnlyMacroCommitmentRecall.Value != nil || report.ByCandidate[0].ScoredOnlyMacroCommitmentRecall.Denominator != 0 || report.ByCandidate[0].ScoredOnlyMicroCommitmentRecall.Value != nil {
		t.Fatal("N/A cases must not become perfect recall")
	}
	alteredReview(t, &envelope, func(r *review) {
		r.Ambiguities = append(r.Ambiguities, ambiguityJudgment{"D01-U2", []string{}, "lost", "The optional proposal is omitted.", envelope.Records[0].Gold.References[6].Evidence})
	})
	result = evaluated(t, envelope).Results[0]
	if !*result.Pass || result.Metrics.RequiredAmbiguity.Denominator != 1 {
		t.Fatal("optional U rows cannot change required denominator")
	}
}

func TestSplitAndCandidateAggregatesKeepAllStatuses(t *testing.T) {
	envelope := positive(t)
	first := envelope.Records[0]
	second := calibration(t).Records[4]
	second.CandidateLabel = first.CandidateLabel
	second.Case.CaseID = "D02"
	second.Case.Split = "held_out"
	second.Gold.CaseID = "D02"
	for i := range second.Gold.References {
		second.Gold.References[i].ID = strings.ReplaceAll(second.Gold.References[i].ID, "D01-", "D02-")
	}
	second.CandidateRaw = strings.ReplaceAll(second.CandidateRaw, "D01", "D02")
	second.Review = json.RawMessage(strings.ReplaceAll(strings.ReplaceAll(string(second.Review), "D01", "D02"), "calibration_05", first.CandidateLabel))
	third := first
	third.CandidateLabel = "unresolved"
	third.Review = json.RawMessage(`null`)
	fourth := first
	fourth.CandidateLabel = "malformed"
	fourth.CandidateRaw = "not JSON"
	envelope.Records = []Record{first, second, third, fourth}
	report := evaluated(t, envelope)
	if len(report.BySplit) != 2 || len(report.ByCandidate) != 3 || len(report.ByCandidateSplit) != 4 {
		t.Fatalf("%+v", report)
	}
	development := report.BySplit[0]
	if development.Cases.Total != 3 || development.Cases.Scored != 1 || development.Cases.Unscorable != 1 || development.Cases.CandidateFailure != 1 || development.ScoredOnlyMicroCommitmentRecall.Denominator != 4 {
		t.Fatalf("%+v", development)
	}
	var combined Aggregate
	for _, group := range report.ByCandidate {
		if group.CandidateLabel == first.CandidateLabel {
			combined = group
		}
	}
	if combined.Cases.Total != 2 || combined.Cases.Passed != 1 || combined.Cases.Failed != 1 || combined.ScoredOnlyMicroCommitmentRecall.Numerator != 5 || combined.ScoredOnlyMicroCommitmentRecall.Denominator != 8 || combined.ScoredOnlyMacroCommitmentRecall.Denominator != 2 || *combined.ScoredOnlyMacroCommitmentRecall.Value != 0.625 {
		t.Fatalf("%+v", combined)
	}
}

func TestEveryRequiredFieldAndUnknownField(t *testing.T) {
	envelope := positive(t)
	var value candidate
	var judgment review
	if err := decode([]byte(envelope.Records[0].CandidateRaw), &value); err != nil {
		t.Fatal(err)
	}
	if err := decode(envelope.Records[0].Review, &judgment); err != nil {
		t.Fatal(err)
	}
	flag := itemFlag{"i0", "omnibus", "Synthetic flag for schema testing.", judgment.Claims[0].SourceQuotes}
	for _, test := range []struct {
		name  string
		value interface{}
	}{
		{"envelope", envelope}, {"record", envelope.Records[0]}, {"case", envelope.Records[0].Case}, {"gold", envelope.Records[0].Gold}, {"reference", envelope.Records[0].Gold.References[0]},
		{"candidate", value}, {"item", value.Items[0]}, {"review", judgment}, {"reference_judgment", judgment.References[0]}, {"claim", judgment.Claims[0]}, {"ambiguity", judgment.Ambiguities[0]}, {"flag", flag},
	} {
		t.Run(test.name, func(t *testing.T) {
			original := rawJSON(t, test.value)
			var fields map[string]json.RawMessage
			if err := json.Unmarshal(original, &fields); err != nil {
				t.Fatal(err)
			}
			for name := range fields {
				if name == "condition" || name == "required" {
					continue
				}
				var altered map[string]json.RawMessage
				if err := json.Unmarshal(original, &altered); err != nil {
					t.Fatal(err)
				}
				delete(altered, name)
				if err := decode(rawJSON(t, altered), reflect.New(reflect.TypeOf(test.value)).Interface()); err == nil {
					t.Errorf("missing %s accepted", name)
				}
			}
			fields["unknown"] = json.RawMessage(`true`)
			if err := decode(rawJSON(t, fields), reflect.New(reflect.TypeOf(test.value)).Interface()); err == nil {
				t.Fatal("unknown field accepted")
			}
		})
	}
}

func TestInclusiveBudgetsAndNoTruncation(t *testing.T) {
	envelope := positive(t)
	var value candidate
	var judgment review
	if err := decode([]byte(envelope.Records[0].CandidateRaw), &value); err != nil {
		t.Fatal(err)
	}
	if err := decode(envelope.Records[0].Review, &judgment); err != nil {
		t.Fatal(err)
	}
	for len(value.Items) < 40 {
		row := value.Items[0]
		row.ID = fmt.Sprintf("extra%d", len(value.Items))
		value.Items = append(value.Items, row)
		claim := judgment.Claims[0]
		claim.ItemID = row.ID
		claim.ClaimID = fmt.Sprintf("extra%d", len(judgment.Claims))
		id := judgment.Claims[0].ClaimID
		claim.DuplicateOf = &id
		judgment.Claims = append(judgment.Claims, claim)
	}
	for len(judgment.Claims) < 100 {
		claim := judgment.Claims[0]
		claim.ClaimID = fmt.Sprintf("extra%d", len(judgment.Claims))
		id := judgment.Claims[0].ClaimID
		claim.DuplicateOf = &id
		judgment.Claims = append(judgment.Claims, claim)
	}
	envelope.Records[0].CandidateRaw = string(rawJSON(t, value))
	envelope.Records[0].Review = rawJSON(t, judgment)
	result := evaluated(t, envelope).Results[0]
	if result.Status != "scored" || !*result.Pass || result.Metrics.Duplicates.Denominator != 100 {
		t.Fatalf("at budget: %+v", result)
	}
	claim := judgment.Claims[0]
	claim.ClaimID = "last"
	judgment.Claims = append(judgment.Claims, claim)
	envelope.Records[0].Review = rawJSON(t, judgment)
	result = evaluated(t, envelope).Results[0]
	if result.Status != "unscorable" || result.Pass != nil || string(result.Input.Review) != string(envelope.Records[0].Review) {
		t.Fatal("over budget review must be preserved without scoring")
	}
}

func TestMicroAndMacroHaveDifferentWeights(t *testing.T) {
	envelope := positive(t)
	second := calibration(t).Records[4]
	second.Gold.References[2].Type = "assumption"
	second.Gold.References[3].Type = "assumption"
	second.Gold.References[4].Type = "assumption"
	envelope.Records = append(envelope.Records, second)
	report := evaluated(t, envelope)
	group := report.BySplit[0]
	if group.ScoredOnlyMicroCommitmentRecall.Numerator != 5 || group.ScoredOnlyMicroCommitmentRecall.Denominator != 5 || *group.ScoredOnlyMacroCommitmentRecall.Value != 1 {
		t.Fatalf("%+v", group)
	}
	alteredReview(t, &envelope, func(r *review) { r.References[1].Coverage = "partial" })
	report = evaluated(t, envelope)
	group = report.BySplit[0]
	if *group.ScoredOnlyMicroCommitmentRecall.Value != 0.8 || *group.ScoredOnlyMacroCommitmentRecall.Value != 0.875 || group.ScoredOnlyMacroCommitmentRecall.Denominator != 2 {
		t.Fatalf("%+v", group)
	}
}

func TestZeroRequiredAmbiguityDenominator(t *testing.T) {
	envelope := positive(t)
	optional := false
	for i := range envelope.Records[0].Gold.References {
		if envelope.Records[0].Gold.References[i].Type == "uncertainty" {
			envelope.Records[0].Gold.References[i].Required = &optional
		}
	}
	alteredReview(t, &envelope, func(r *review) { r.Ambiguities = []ambiguityJudgment{} })
	result := evaluated(t, envelope).Results[0]
	if !*result.Pass || result.Metrics.RequiredAmbiguity.Value != nil || result.Metrics.RequiredAmbiguity.Denominator != 0 {
		t.Fatalf("%+v", result)
	}
}
