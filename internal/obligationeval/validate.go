package obligationeval

import (
	"bytes"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

var identifier = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]*$`)

func member(value string, choices ...string) bool {
	for _, choice := range choices {
		if value == choice {
			return true
		}
	}
	return false
}

func nonempty(value string) bool { return strings.TrimSpace(value) != "" }

func validQuotes(quotes []string, source string) bool {
	if len(quotes) == 0 {
		return false
	}
	for _, quote := range quotes {
		if !nonempty(quote) || !strings.Contains(source, quote) {
			return false
		}
	}
	return true
}

func validKind(kind string) bool {
	return member(kind, "goal", "obligation", "constraint", "assumption", "question")
}

func validateInput(record Record) error {
	if !identifier.MatchString(record.CandidateLabel) || !identifier.MatchString(record.Case.CaseID) || !member(record.Case.Split, "development", "held_out") || !nonempty(record.Case.Request) {
		return fmt.Errorf("invalid candidate label, case ID, split or request")
	}
	if record.Gold.CaseID != record.Case.CaseID || !nonempty(record.Gold.GoldVersion) {
		return fmt.Errorf("invalid gold identity/version")
	}
	seen := map[string]bool{}
	for _, ref := range record.Gold.References {
		if !identifier.MatchString(ref.ID) || seen[ref.ID] || !strings.HasPrefix(ref.ID, record.Case.CaseID+"-") {
			return fmt.Errorf("invalid or duplicate gold reference ID %q", ref.ID)
		}
		seen[ref.ID] = true
		if !member(ref.Type, "goal", "commitment", "assumption", "uncertainty") || !nonempty(ref.Text) || !validQuotes(ref.Evidence, record.Case.Request) {
			return fmt.Errorf("invalid gold reference %q", ref.ID)
		}
		if len(ref.AcceptedKinds) == 0 {
			return fmt.Errorf("gold reference %q has no accepted kinds", ref.ID)
		}
		kinds := map[string]bool{}
		for _, kind := range ref.AcceptedKinds {
			if !validKind(kind) || kinds[kind] {
				return fmt.Errorf("invalid or repeated accepted kind for %q", ref.ID)
			}
			kinds[kind] = true
		}
		if ref.Required != nil && ref.Type != "uncertainty" {
			return fmt.Errorf("required is only defined for uncertainty references")
		}
		if len(ref.Condition) > 0 && !bytes.Equal(bytes.TrimSpace(ref.Condition), []byte("null")) {
			var condition string
			if err := json.Unmarshal(ref.Condition, &condition); err != nil || !nonempty(condition) {
				return fmt.Errorf("invalid condition for %q", ref.ID)
			}
		}
	}
	for _, note := range record.Gold.ReviewNotes {
		if !nonempty(note) {
			return fmt.Errorf("empty gold review note")
		}
	}
	return nil
}

func validateCandidate(value candidate, caseID string) error {
	if value.CaseID != caseID {
		return fmt.Errorf("candidate case ID mismatch")
	}
	seen := map[string]bool{}
	for _, item := range value.Items {
		if !identifier.MatchString(item.ID) || seen[item.ID] || !validKind(item.Kind) || !nonempty(item.Text) {
			return fmt.Errorf("invalid or duplicate candidate item %q", item.ID)
		}
		seen[item.ID] = true
		for _, quote := range item.Evidence {
			if !nonempty(quote) {
				return fmt.Errorf("empty candidate evidence quote in %q", item.ID)
			}
		}
	}
	return nil
}

func validateReview(value review, record Record, candidate candidate) error {
	if value.CaseID != record.Case.CaseID || value.CandidateLabel != record.CandidateLabel || value.GoldVersion != record.Gold.GoldVersion {
		return fmt.Errorf("review identity/version mismatch")
	}
	if !member(value.ReviewStatus, "complete", "needs_adjudication") {
		return fmt.Errorf("invalid review status")
	}
	if len(value.Claims) > 100 {
		return fmt.Errorf("review exceeds 100 claims")
	}
	if value.ReviewStatus != "complete" || len(value.Disagreements) != 0 {
		return fmt.Errorf("review needs adjudication or has unresolved disagreement")
	}
	items := map[string]item{}
	for _, item := range candidate.Items {
		items[item.ID] = item
	}
	refs := map[string]Reference{}
	for _, ref := range record.Gold.References {
		refs[ref.ID] = ref
	}
	seen := map[string]bool{}
	for _, row := range value.References {
		if _, ok := refs[row.ReferenceID]; !ok || seen[row.ReferenceID] {
			return fmt.Errorf("unknown or repeated reference judgment %q", row.ReferenceID)
		}
		seen[row.ReferenceID] = true
		if !member(row.Coverage, "full", "partial", "missing") || (row.Coverage != "missing" && len(row.ItemIDs) == 0) {
			return fmt.Errorf("invalid coverage for %q", row.ReferenceID)
		}
		if err := validateRow(row.ItemIDs, row.Rationale, row.SourceQuotes, record.Case.Request, items); err != nil {
			return err
		}
	}
	if len(seen) != len(refs) {
		return fmt.Errorf("incomplete reference judgments")
	}
	claims := map[string]bool{}
	accounted := map[string]bool{}
	for _, row := range value.Claims {
		item, ok := items[row.ItemID]
		if !ok || !identifier.MatchString(row.ClaimID) || claims[row.ClaimID] || !nonempty(row.CandidateFragment) || !strings.Contains(item.Text, row.CandidateFragment) {
			return fmt.Errorf("invalid claim ID, item or fragment %q", row.ClaimID)
		}
		if !member(row.Verdict, "supported", "unsupported", "contradicted", "explicit_proposal", "open_question") {
			return fmt.Errorf("invalid claim verdict")
		}
		if row.DuplicateOf != nil && !claims[*row.DuplicateOf] {
			return fmt.Errorf("duplicate link must point to an earlier claim")
		}
		if err := validateRow([]string{row.ItemID}, row.Rationale, row.SourceQuotes, record.Case.Request, items); err != nil {
			return err
		}
		claims[row.ClaimID] = true
		accounted[row.ItemID] = true
	}
	if len(accounted) != len(items) {
		return fmt.Errorf("not all candidate items have claim judgments")
	}
	ambiguities := map[string]bool{}
	for _, row := range value.Ambiguities {
		ref, ok := refs[row.ReferenceID]
		if !ok || ref.Type != "uncertainty" || ambiguities[row.ReferenceID] {
			return fmt.Errorf("invalid or repeated ambiguity reference")
		}
		ambiguities[row.ReferenceID] = true
		if !member(row.Status, "preserved", "lost", "resolved_without_authority") || (row.Status != "lost" && len(row.ItemIDs) == 0) {
			return fmt.Errorf("invalid ambiguity status or missing item IDs")
		}
		if err := validateRow(row.ItemIDs, row.Rationale, row.SourceQuotes, record.Case.Request, items); err != nil {
			return err
		}
	}
	for _, ref := range record.Gold.References {
		if ref.Type == "uncertainty" && (ref.Required == nil || *ref.Required) && !ambiguities[ref.ID] {
			return fmt.Errorf("missing required ambiguity judgment %q", ref.ID)
		}
	}
	flags := map[[2]string]bool{}
	for _, row := range value.Flags {
		key := [2]string{row.ItemID, row.Flag}
		if !member(row.Flag, "material_role_error", "nonmaterial_role_mismatch", "omnibus") || flags[key] {
			return fmt.Errorf("unknown or duplicate flag")
		}
		flags[key] = true
		if err := validateRow([]string{row.ItemID}, row.Rationale, row.SourceQuotes, record.Case.Request, items); err != nil {
			return err
		}
	}
	return nil
}

func validateRow(ids []string, rationale string, quotes []string, source string, items map[string]item) error {
	if !nonempty(rationale) || !validQuotes(quotes, source) {
		return fmt.Errorf("review requires a rationale and nonempty verbatim source quotes")
	}
	seen := map[string]bool{}
	for _, id := range ids {
		if _, ok := items[id]; !ok || seen[id] {
			return fmt.Errorf("unknown or repeated item reference %q", id)
		}
		seen[id] = true
	}
	return nil
}
