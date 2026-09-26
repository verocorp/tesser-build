package experiment

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type TrialOptions struct {
	Verification      Options
	Agent             []string
	Arm               string
	InterventionsPath string
}

type InterventionEvent struct {
	At          time.Time `json:"at"`
	Kind        string    `json:"kind"`
	Description string    `json:"description"`
}

type InterventionEvidence struct {
	Status string              `json:"status"`
	Events []InterventionEvent `json:"events"`
	Error  string              `json:"error,omitempty"`
}

type TrialResult struct {
	Version             int                  `json:"version"`
	MeasurementScope    string               `json:"measurement_scope"`
	Arm                 string               `json:"arm"`
	ScenarioID          string               `json:"scenario_id"`
	Family              string               `json:"family"`
	Followup            string               `json:"followup,omitempty"`
	ConfigurationDigest string               `json:"configuration_digest"`
	ContractDigest      string               `json:"contract_digest"`
	InitialSourceDigest string               `json:"initial_source_digest"`
	Status              string               `json:"status"`
	Eligible            bool                 `json:"eligible"`
	Error               string               `json:"error,omitempty"`
	TaskReleasedAt      time.Time            `json:"task_released_at"`
	TaskDeadlineAt      time.Time            `json:"task_deadline_at"`
	TaskEndedAt         time.Time            `json:"task_ended_at"`
	VerifiedAt          *time.Time           `json:"verified_at"`
	TaskElapsedMS       int64                `json:"task_elapsed_ms"`
	TaskBudgetMS        int64                `json:"task_budget_ms"`
	CappedCompletionMS  *int64               `json:"capped_completion_ms"`
	Agent               *StageResult         `json:"agent"`
	Verification        *Result              `json:"verification"`
	Usage               string               `json:"usage"`
	Cost                string               `json:"cost"`
	HumanIntervention   InterventionEvidence `json:"human_intervention"`
	SafetyNotice        string               `json:"safety_notice"`
}

func RunTrial(parent context.Context, options TrialOptions) (result TrialResult) {
	released := time.Now().UTC()
	result = TrialResult{
		Version: 1, MeasurementScope: "local_agent_process_through_verification", Arm: options.Arm,
		Status: InfraError, TaskReleasedAt: released, TaskDeadlineAt: released.Add(options.Verification.Deadline),
		TaskBudgetMS: options.Verification.Deadline.Milliseconds(), Usage: "unknown", Cost: "unknown",
		HumanIntervention: InterventionEvidence{Status: "unknown"}, SafetyNotice: SafetyNotice,
	}
	ctx, cancel := context.WithDeadline(parent, result.TaskDeadlineAt)
	defer cancel()
	defer func() {
		result.TaskEndedAt = time.Now().UTC()
		result.TaskElapsedMS = result.TaskEndedAt.Sub(released).Milliseconds()
		if ctx.Err() != nil && result.Status == Correct {
			result.Status, result.Error = contextStatus(ctx), ctx.Err().Error()
		}
		if options.InterventionsPath != "" {
			result.HumanIntervention = readInterventions(options.InterventionsPath)
			if result.HumanIntervention.Error != "" && result.Status == Correct {
				result.Status, result.Error = InfraError, result.HumanIntervention.Error
			}
		}
		if result.Eligible {
			capped := result.TaskBudgetMS
			if result.Status == Correct {
				verified := result.Verification.VerificationEndedAt
				result.VerifiedAt = &verified
				capped = min(verified.Sub(released).Milliseconds(), result.TaskBudgetMS)
			}
			result.CappedCompletionMS = &capped
		}
	}()
	if options.Verification.Deadline < time.Millisecond || strings.TrimSpace(options.Arm) == "" {
		result.Error = "trial requires an arm id and a whole-task deadline of at least 1ms"
		return
	}
	for _, argv := range append([][]string{options.Agent, options.Verification.Command}, options.Verification.Gates...) {
		if err := validateCommand(argv); err != nil {
			result.Error = err.Error()
			return
		}
	}
	scenario, err := LoadScenario(options.Verification.ScenarioPath)
	if err != nil {
		result.Error = err.Error()
		return
	}
	brief, err := scenario.Brief(options.Verification.Followup)
	if err != nil {
		result.Error = err.Error()
		return
	}
	result.ContractDigest = scenario.digest
	result.ScenarioID, result.Family, result.Followup = scenario.contract.ID, scenario.contract.Family, options.Verification.Followup
	source, err := filepath.Abs(options.Verification.CandidateDir)
	if err != nil || options.Verification.CandidateDir == "" {
		result.Error = "candidate directory is required"
		return
	}
	source, err = candidatePath(source)
	if err != nil {
		result.Error = err.Error()
		return
	}
	oracle, err := filepath.Abs(options.Verification.ScenarioPath)
	if err == nil {
		oracle, err = filepath.EvalSymlinks(oracle)
	}
	if err != nil || ContainsPath(source, oracle) {
		result.Error = "scenario oracle must be outside the candidate tree"
		return
	}
	configuration, err := json.Marshal(struct {
		Arm      string
		Agent    []string
		Command  []string
		Gates    [][]string
		Followup string
		BudgetNS int64
	}{options.Arm, options.Agent, options.Verification.Command, options.Verification.Gates, options.Verification.Followup, int64(options.Verification.Deadline)})
	if err != nil {
		result.Error = err.Error()
		return
	}
	digest := sha256.Sum256(configuration)
	result.ConfigurationDigest = hex.EncodeToString(digest[:])
	result.InitialSourceDigest, err = treeDigest(ctx, source, false)
	if err != nil {
		result.Error = err.Error()
		if ctx.Err() != nil {
			result.Status = contextStatus(ctx)
		}
		return
	}
	result.Eligible = true
	prompt, err := json.Marshal(brief)
	if err != nil {
		result.Error = err.Error()
		return
	}
	agent := runStage(ctx, source, options.Agent, "gate", "agent", []json.RawMessage{prompt}, nil)
	agent.Kind = "agent"
	result.Agent = &agent
	if agent.Status != Correct {
		result.Status, result.Error = agent.Status, "agent: "+agent.Error
		return
	}
	if ctx.Err() != nil {
		result.Status, result.Error = contextStatus(ctx), ctx.Err().Error()
		return
	}
	current, err := LoadScenario(options.Verification.ScenarioPath)
	if err != nil || current.digest != scenario.digest {
		result.Error = "scenario oracle changed during agent execution"
		return
	}
	verificationOptions := options.Verification
	verificationOptions.Deadline = time.Until(result.TaskDeadlineAt)
	if verificationOptions.Deadline <= 0 {
		result.Status, result.Error = Timeout, "whole-task deadline exhausted before verification"
		return
	}
	verification := Verify(ctx, verificationOptions)
	result.Verification = &verification
	result.Status, result.Error = verification.Status, verification.Error
	if verification.ContractDigest != scenario.digest {
		result.Status, result.Error = InfraError, "scenario oracle changed before verification"
	}
	return
}

func readInterventions(path string) InterventionEvidence {
	evidence := InterventionEvidence{Status: "unknown"}
	info, err := os.Stat(path)
	if err != nil || !info.Mode().IsRegular() {
		evidence.Error = "intervention input must be a readable regular JSON file"
		return evidence
	}
	file, err := os.Open(path)
	if err != nil {
		evidence.Error = err.Error()
		return evidence
	}
	defer file.Close()
	data, err := io.ReadAll(io.LimitReader(file, maxJSONBytes+1))
	if err != nil || len(data) > maxJSONBytes {
		evidence.Error = "intervention input exceeds its read limit"
		return evidence
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&evidence.Events); err != nil || evidence.Events == nil {
		evidence.Error = "intervention input must be an array of timestamped events"
		return evidence
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		evidence.Error = "intervention input has trailing data"
		return evidence
	}
	for _, event := range evidence.Events {
		if event.At.IsZero() || strings.TrimSpace(event.Kind) == "" || strings.TrimSpace(event.Description) == "" {
			evidence.Error = "intervention event requires at, kind, and description"
			return evidence
		}
	}
	evidence.Status = "reported"
	return evidence
}
