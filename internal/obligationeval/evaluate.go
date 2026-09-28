package obligationeval

import (
	"fmt"
	"sort"
	"strings"
)

func Evaluate(input []byte) (Report, error) {
	var envelope Envelope
	if err := decode(input, &envelope); err != nil {
		return Report{}, err
	}
	if envelope.SchemaVersion != SchemaVersion || len(envelope.Records) == 0 || len(envelope.Records) > 1000 {
		return Report{}, fmt.Errorf("expected %s and 1..1000 records", SchemaVersion)
	}
	seen := map[[2]string]bool{}
	for i, record := range envelope.Records {
		if err := validateInput(record); err != nil {
			return Report{}, fmt.Errorf("records[%d]: %w", i, err)
		}
		key := [2]string{record.CandidateLabel, record.Case.CaseID}
		if seen[key] {
			return Report{}, fmt.Errorf("duplicate candidate/case pair %q/%q", key[0], key[1])
		}
		seen[key] = true
	}
	report := Report{SchemaVersion: SchemaVersion, Results: make([]Result, 0, len(envelope.Records))}
	for _, record := range envelope.Records {
		report.Results = append(report.Results, evaluateRecord(record))
	}
	report.ByCandidate = aggregate(report.Results, true, false)
	report.BySplit = aggregate(report.Results, false, true)
	report.ByCandidateSplit = aggregate(report.Results, true, true)
	return report, nil
}

func evaluateRecord(record Record) Result {
	result := Result{Input: record, Status: "candidate_failure", Reasons: []string{}}
	var candidate candidate
	if err := decode([]byte(record.CandidateRaw), &candidate); err != nil {
		result.Reasons = append(result.Reasons, err.Error())
		return result
	}
	if err := validateCandidate(candidate, record.Case.CaseID); err != nil {
		result.Reasons = append(result.Reasons, err.Error())
		return result
	}
	result.CandidateFormatValid = true
	grounding := Grounding{}
	for _, item := range candidate.Items {
		valid := 0
		for _, quote := range item.Evidence {
			grounding.Denominator++
			if strings.Contains(record.Case.Request, quote) {
				grounding.Numerator++
				valid++
			}
		}
		if valid == 0 {
			grounding.ItemsWithoutValidQuote++
		}
	}
	grounding.Ratio = ratio(grounding.Numerator, grounding.Denominator)
	result.Grounding = &grounding
	if len(candidate.Items) > 40 {
		result.Status = "unscorable"
		result.Reasons = append(result.Reasons, "candidate exceeds 40 items")
		return result
	}
	var judgment review
	if err := decode(record.Review, &judgment); err != nil {
		result.Status = "unscorable"
		result.Reasons = append(result.Reasons, "invalid review: "+err.Error())
		return result
	}
	if err := validateReview(judgment, record, candidate); err != nil {
		result.Status = "unscorable"
		result.Reasons = append(result.Reasons, err.Error())
		return result
	}
	if grounding.Numerator != grounding.Denominator || grounding.ItemsWithoutValidQuote > 0 {
		result.Reasons = append(result.Reasons, "candidate evidence has invalid or missing source quotes")
		return result
	}
	metrics := score(record.Gold, judgment)
	result.Metrics = &metrics
	result.Status = "scored"
	pass := len(candidate.Items) > 0 && metrics.CommitmentRecall.Numerator == metrics.CommitmentRecall.Denominator && metrics.GoalCoverage.Numerator == metrics.GoalCoverage.Denominator && metrics.AssumptionCoverage.Numerator == metrics.AssumptionCoverage.Denominator && metrics.RequiredAmbiguity.Numerator == metrics.RequiredAmbiguity.Denominator && metrics.UnsupportedClaims == 0 && metrics.ContradictedClaims == 0 && metrics.MaterialRoleErrors == 0 && metrics.OmnibusItems == 0
	result.Pass = &pass
	return result
}

func ratio(numerator, denominator int) Ratio {
	value := Ratio{Numerator: numerator, Denominator: denominator}
	if denominator != 0 {
		fraction := float64(numerator) / float64(denominator)
		value.Value = &fraction
	}
	return value
}

func score(gold Gold, judgment review) Metrics {
	metrics := Metrics{}
	coverage := map[string]string{}
	for _, row := range judgment.References {
		coverage[row.ReferenceID] = row.Coverage
	}
	ambiguity := map[string]string{}
	for _, row := range judgment.Ambiguities {
		ambiguity[row.ReferenceID] = row.Status
	}
	for _, ref := range gold.References {
		var target *Coverage
		switch ref.Type {
		case "commitment":
			target = &metrics.CommitmentRecall
		case "goal":
			target = &metrics.GoalCoverage
		case "assumption":
			target = &metrics.AssumptionCoverage
		case "uncertainty":
			if ref.Required == nil || *ref.Required {
				metrics.RequiredAmbiguity.Denominator++
				if ambiguity[ref.ID] == "preserved" {
					metrics.RequiredAmbiguity.Numerator++
				}
			}
		}
		if target != nil {
			target.Denominator++
			switch coverage[ref.ID] {
			case "full":
				target.Numerator++
			case "partial":
				target.Partial++
			case "missing":
				target.Missing++
			}
		}
	}
	for _, target := range []*Coverage{&metrics.CommitmentRecall, &metrics.GoalCoverage, &metrics.AssumptionCoverage} {
		target.Ratio = ratio(target.Numerator, target.Denominator)
	}
	metrics.RequiredAmbiguity = ratio(metrics.RequiredAmbiguity.Numerator, metrics.RequiredAmbiguity.Denominator)
	for _, claim := range judgment.Claims {
		if claim.Verdict == "unsupported" {
			metrics.UnsupportedClaims++
		}
		if claim.Verdict == "contradicted" {
			metrics.ContradictedClaims++
		}
		if claim.DuplicateOf != nil {
			metrics.Duplicates.Numerator++
			continue
		}
		if member(claim.Verdict, "supported", "unsupported", "contradicted") {
			metrics.AssertionPrecision.Denominator++
			if claim.Verdict == "supported" {
				metrics.AssertionPrecision.Numerator++
			}
		}
	}
	metrics.AssertionPrecision = ratio(metrics.AssertionPrecision.Numerator, metrics.AssertionPrecision.Denominator)
	metrics.Duplicates = ratio(metrics.Duplicates.Numerator, len(judgment.Claims))
	for _, flag := range judgment.Flags {
		switch flag.Flag {
		case "material_role_error":
			metrics.MaterialRoleErrors++
		case "nonmaterial_role_mismatch":
			metrics.NonmaterialRoleMismatches++
		case "omnibus":
			metrics.OmnibusItems++
		}
	}
	return metrics
}

func aggregate(results []Result, byCandidate, bySplit bool) []Aggregate {
	groups := map[[2]string]*Aggregate{}
	for _, result := range results {
		key := [2]string{}
		if byCandidate {
			key[0] = result.Input.CandidateLabel
		}
		if bySplit {
			key[1] = result.Input.Case.Split
		}
		group := groups[key]
		if group == nil {
			group = &Aggregate{CandidateLabel: key[0], Split: key[1]}
			groups[key] = group
		}
		group.Cases.Total++
		switch result.Status {
		case "candidate_failure":
			group.Cases.CandidateFailure++
		case "unscorable":
			group.Cases.Unscorable++
		case "scored":
			group.Cases.Scored++
			if *result.Pass {
				group.Cases.Passed++
			} else {
				group.Cases.Failed++
			}
			metric := result.Metrics.CommitmentRecall
			group.ScoredOnlyMicroCommitmentRecall.Numerator += metric.Numerator
			group.ScoredOnlyMicroCommitmentRecall.Denominator += metric.Denominator
			if metric.Value != nil {
				group.ScoredOnlyMacroCommitmentRecall.Sum += *metric.Value
				group.ScoredOnlyMacroCommitmentRecall.Denominator++
			}
		}
	}
	output := make([]Aggregate, 0, len(groups))
	for _, group := range groups {
		group.ScoredOnlyMicroCommitmentRecall = ratio(group.ScoredOnlyMicroCommitmentRecall.Numerator, group.ScoredOnlyMicroCommitmentRecall.Denominator)
		if group.ScoredOnlyMacroCommitmentRecall.Denominator > 0 {
			value := group.ScoredOnlyMacroCommitmentRecall.Sum / float64(group.ScoredOnlyMacroCommitmentRecall.Denominator)
			group.ScoredOnlyMacroCommitmentRecall.Value = &value
		}
		output = append(output, *group)
	}
	sort.Slice(output, func(i, j int) bool {
		if output[i].CandidateLabel != output[j].CandidateLabel {
			return output[i].CandidateLabel < output[j].CandidateLabel
		}
		return output[i].Split < output[j].Split
	})
	return output
}
