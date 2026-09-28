package obligationeval

import "encoding/json"

const SchemaVersion = "obligations-eval-v1"

type Envelope struct {
	SchemaVersion string   `json:"schema_version"`
	Records       []Record `json:"records"`
}

type Record struct {
	CandidateLabel string          `json:"candidate_label"`
	Case           Case            `json:"case"`
	Gold           Gold            `json:"gold"`
	CandidateRaw   string          `json:"candidate_raw"`
	Review         json.RawMessage `json:"review" nullable:"true"`
}

type Case struct {
	CaseID  string `json:"case_id"`
	Split   string `json:"split"`
	Request string `json:"request"`
}

type Gold struct {
	GoldVersion string      `json:"gold_version"`
	CaseID      string      `json:"case_id"`
	References  []Reference `json:"references"`
	ReviewNotes []string    `json:"review_notes"`
}

type Reference struct {
	ID            string          `json:"id"`
	Type          string          `json:"type"`
	AcceptedKinds []string        `json:"accepted_kinds"`
	Text          string          `json:"text"`
	Evidence      []string        `json:"evidence"`
	Condition     json.RawMessage `json:"condition,omitempty" optional:"true" nullable:"true"`
	Required      *bool           `json:"required,omitempty" optional:"true"`
}

type candidate struct {
	CaseID string `json:"case_id"`
	Items  []item `json:"items"`
}

type item struct {
	ID       string   `json:"id"`
	Kind     string   `json:"kind"`
	Text     string   `json:"text"`
	Evidence []string `json:"evidence"`
}

type review struct {
	CaseID         string              `json:"case_id"`
	CandidateLabel string              `json:"candidate_label"`
	GoldVersion    string              `json:"gold_version"`
	ReviewStatus   string              `json:"review_status"`
	References     []referenceJudgment `json:"reference_judgments"`
	Claims         []claimJudgment     `json:"claim_judgments"`
	Ambiguities    []ambiguityJudgment `json:"ambiguity_judgments"`
	Flags          []itemFlag          `json:"item_flags"`
	Disagreements  []json.RawMessage   `json:"disagreements"`
}

type referenceJudgment struct {
	ReferenceID  string   `json:"reference_id"`
	ItemIDs      []string `json:"item_ids"`
	Coverage     string   `json:"coverage"`
	Rationale    string   `json:"rationale"`
	SourceQuotes []string `json:"source_quotes"`
}

type claimJudgment struct {
	ClaimID           string   `json:"claim_id"`
	ItemID            string   `json:"item_id"`
	CandidateFragment string   `json:"candidate_fragment"`
	Verdict           string   `json:"verdict"`
	DuplicateOf       *string  `json:"duplicate_of" nullable:"true"`
	Rationale         string   `json:"rationale"`
	SourceQuotes      []string `json:"source_quotes"`
}

type ambiguityJudgment struct {
	ReferenceID  string   `json:"reference_id"`
	ItemIDs      []string `json:"item_ids"`
	Status       string   `json:"status"`
	Rationale    string   `json:"rationale"`
	SourceQuotes []string `json:"source_quotes"`
}

type itemFlag struct {
	ItemID       string   `json:"item_id"`
	Flag         string   `json:"flag"`
	Rationale    string   `json:"rationale"`
	SourceQuotes []string `json:"source_quotes"`
}

type Ratio struct {
	Numerator   int      `json:"numerator"`
	Denominator int      `json:"denominator"`
	Value       *float64 `json:"value"`
}

type Coverage struct {
	Ratio
	Partial int `json:"partial"`
	Missing int `json:"missing"`
}

type Grounding struct {
	Ratio
	ItemsWithoutValidQuote int `json:"items_without_valid_quote"`
}

type Metrics struct {
	CommitmentRecall          Coverage `json:"commitment_recall"`
	GoalCoverage              Coverage `json:"goal_coverage"`
	AssumptionCoverage        Coverage `json:"source_assumption_coverage"`
	RequiredAmbiguity         Ratio    `json:"required_ambiguity_preservation"`
	AssertionPrecision        Ratio    `json:"assertion_precision"`
	Duplicates                Ratio    `json:"duplicates"`
	UnsupportedClaims         int      `json:"unsupported_claims"`
	ContradictedClaims        int      `json:"contradicted_claims"`
	MaterialRoleErrors        int      `json:"material_role_errors"`
	NonmaterialRoleMismatches int      `json:"nonmaterial_role_mismatches"`
	OmnibusItems              int      `json:"omnibus_items"`
}

type Result struct {
	Input                Record     `json:"input"`
	Status               string     `json:"status"`
	Pass                 *bool      `json:"pass"`
	Reasons              []string   `json:"reasons"`
	CandidateFormatValid bool       `json:"candidate_format_valid"`
	Grounding            *Grounding `json:"grounding"`
	Metrics              *Metrics   `json:"metrics"`
}

type CaseCounts struct {
	Total            int `json:"total"`
	Scored           int `json:"scored"`
	CandidateFailure int `json:"candidate_failure"`
	Unscorable       int `json:"unscorable"`
	Passed           int `json:"passed"`
	Failed           int `json:"failed"`
}

type MacroRecall struct {
	Sum         float64  `json:"sum_of_case_recalls"`
	Denominator int      `json:"scored_cases_with_commitments"`
	Value       *float64 `json:"value"`
}

type Aggregate struct {
	CandidateLabel                  string      `json:"candidate_label,omitempty"`
	Split                           string      `json:"split,omitempty"`
	Cases                           CaseCounts  `json:"cases"`
	ScoredOnlyMicroCommitmentRecall Ratio       `json:"scored_only_micro_commitment_recall"`
	ScoredOnlyMacroCommitmentRecall MacroRecall `json:"scored_only_macro_commitment_recall"`
}

type Report struct {
	SchemaVersion    string      `json:"schema_version"`
	Results          []Result    `json:"results"`
	ByCandidate      []Aggregate `json:"by_candidate"`
	BySplit          []Aggregate `json:"by_split"`
	ByCandidateSplit []Aggregate `json:"by_candidate_split"`
}
