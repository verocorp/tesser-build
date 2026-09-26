package experiment

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	Correct    = "correct"
	Incorrect  = "incorrect"
	Timeout    = "timeout"
	InfraError = "infra_error"
)

type Options struct {
	ScenarioPath string
	CandidateDir string
	Command      []string
	Gates        [][]string
	Deadline     time.Duration
	Followup     string
}

type Result struct {
	Version               int           `json:"version"`
	ScenarioID            string        `json:"scenario_id"`
	Family                string        `json:"family"`
	Followup              string        `json:"followup,omitempty"`
	Status                string        `json:"status"`
	Eligible              bool          `json:"eligible"`
	Error                 string        `json:"error,omitempty"`
	VerificationStartedAt time.Time     `json:"verification_started_at"`
	VerificationEndedAt   time.Time     `json:"verification_ended_at"`
	VerificationElapsedMS int64         `json:"verification_elapsed_ms"`
	VerificationBudgetMS  int64         `json:"verification_budget_ms"`
	SourceDigest          string        `json:"source_digest"`
	ContractDigest        string        `json:"contract_digest"`
	Stages                []StageResult `json:"stages"`
	Usage                 string        `json:"usage"`
	Cost                  string        `json:"cost"`
	HumanIntervention     string        `json:"human_intervention"`
	SafetyNotice          string        `json:"safety_notice"`
}

type StageResult struct {
	Kind            string    `json:"kind"`
	ID              string    `json:"id"`
	Status          string    `json:"status"`
	ExitCode        *int      `json:"exit_code"`
	Error           string    `json:"error,omitempty"`
	Stderr          string    `json:"stderr"`
	StderrTruncated bool      `json:"stderr_truncated"`
	StartedAt       time.Time `json:"started_at"`
	EndedAt         time.Time `json:"ended_at"`
	ElapsedMS       int64     `json:"elapsed_ms"`
	Responses       int       `json:"responses"`
}

func Verify(parent context.Context, options Options) (result Result) {
	result = Result{
		Version: 1, Followup: options.Followup, Status: InfraError,
		VerificationStartedAt: time.Now().UTC(), VerificationBudgetMS: options.Deadline.Milliseconds(),
		Stages: []StageResult{}, Usage: "unknown", Cost: "unknown", HumanIntervention: "unknown", SafetyNotice: SafetyNotice,
	}
	ctx, cancel := context.WithTimeout(parent, options.Deadline)
	defer cancel()
	defer func() {
		if ctx.Err() != nil && (result.Status == Correct || result.Status == InfraError) && options.Deadline > 0 {
			result.Status = contextStatus(ctx)
			if result.Error == "" {
				result.Error = ctx.Err().Error()
			}
		}
		result.VerificationEndedAt = time.Now().UTC()
		result.VerificationElapsedMS = result.VerificationEndedAt.Sub(result.VerificationStartedAt).Milliseconds()
	}()
	if options.Deadline <= 0 {
		result.Error = "deadline must be positive"
		return
	}
	if err := validateCommand(options.Command); err != nil {
		result.Error = err.Error()
		return
	}
	for _, gate := range options.Gates {
		if err := validateCommand(gate); err != nil {
			result.Error = "gate: " + err.Error()
			return
		}
	}
	scenario, err := LoadScenario(options.ScenarioPath)
	if err != nil {
		result.Error = err.Error()
		return
	}
	result.ScenarioID = scenario.contract.ID
	result.Family = scenario.contract.Family
	result.ContractDigest = scenario.digest
	probes, _, err := scenario.selected(options.Followup)
	if err != nil {
		result.Error = err.Error()
		return
	}
	source, err := filepath.Abs(options.CandidateDir)
	if err != nil || options.CandidateDir == "" {
		result.Error = "candidate directory is required"
		return
	}
	source, err = candidatePath(source)
	if err != nil {
		result.Error = "candidate: " + err.Error()
		return
	}
	contractPath, err := filepath.EvalSymlinks(options.ScenarioPath)
	if err == nil {
		contractPath, err = filepath.Abs(contractPath)
	}
	if err != nil || ContainsPath(source, contractPath) {
		result.Error = "scenario oracle must be outside the candidate tree"
		return
	}
	temporaryRoot, err := filepath.EvalSymlinks(os.TempDir())
	if err == nil {
		temporaryRoot, err = filepath.Abs(temporaryRoot)
	}
	if err != nil || ContainsPath(source, temporaryRoot) {
		result.Error = "temporary directory must exist outside the candidate tree"
		return
	}
	owned, err := os.MkdirTemp(temporaryRoot, "tesser-experiment-")
	if err != nil {
		result.Error = "create snapshot directory: " + err.Error()
		return
	}
	defer removeSnapshot(owned)
	snapshot := filepath.Join(owned, "candidate")
	result.SourceDigest, err = treeDigest(ctx, source, false)
	if err != nil {
		result.Error = "hash candidate: " + err.Error()
		return
	}
	sourceMetadata, err := treeDigest(ctx, source, true)
	if err != nil {
		result.Error = "hash candidate metadata: " + err.Error()
		return
	}
	if err = copyTree(ctx, source, snapshot); err != nil {
		result.Error = "copy candidate: " + err.Error()
		return
	}
	for _, directory := range []string{source, snapshot} {
		digest, err := treeDigest(ctx, directory, true)
		if err != nil || digest != sourceMetadata {
			result.Error = "candidate changed while preparing snapshot"
			if err != nil {
				result.Error += ": " + err.Error()
			}
			return
		}
	}
	baseline, err := treeDigest(ctx, snapshot, true)
	if err != nil {
		result.Error = "hash snapshot: " + err.Error()
		return
	}
	watch, err := watchMutations(ctx, snapshot)
	if err != nil {
		result.Error = "watch snapshot: " + err.Error()
		return
	}
	defer watch.close()
	result.Eligible = true
	result.Status = Correct
	for index, argv := range options.Gates {
		stage := runStage(ctx, snapshot, snapshotCommand(argv, source, snapshot), "gate", fmt.Sprintf("gate-%d", index+1), nil, nil)
		checkIntegrity(ctx, snapshot, baseline, watch, &stage)
		result.Stages = append(result.Stages, stage)
		if stage.Status != Correct {
			result.Status, result.Error = stage.Status, stage.Error
			return
		}
	}
	for _, p := range probes {
		stage := runStage(ctx, snapshot, snapshotCommand(options.Command, source, snapshot), "probe", p.ID, p.Inputs, p.Expected)
		checkIntegrity(ctx, snapshot, baseline, watch, &stage)
		result.Stages = append(result.Stages, stage)
		if stage.Status != Correct {
			result.Status, result.Error = stage.Status, stage.Error
			return
		}
	}
	return
}

func validateCommand(argv []string) error {
	if len(argv) == 0 || strings.TrimSpace(argv[0]) == "" {
		return fmt.Errorf("command must be a nonempty JSON argv array")
	}
	for _, argument := range argv {
		if strings.ContainsRune(argument, 0) {
			return fmt.Errorf("command arguments must not contain NUL")
		}
	}
	return nil
}

func snapshotCommand(argv []string, source, snapshot string) []string {
	command := append([]string(nil), argv...)
	for index, argument := range command {
		if !filepath.IsAbs(argument) {
			continue
		}
		if !ContainsPath(source, argument) {
			if resolved, err := filepath.EvalSymlinks(argument); err == nil {
				argument = resolved
			}
		}
		if ContainsPath(source, argument) {
			relative, err := filepath.Rel(source, argument)
			if err == nil {
				command[index] = filepath.Join(snapshot, relative)
			}
		}
	}
	return command
}

func checkIntegrity(ctx context.Context, snapshot, baseline string, watch *mutationWatch, stage *StageResult) {
	changed, watchErr := watch.changed()
	if stage.Status == Correct && (changed || watchErr != nil) {
		stage.Status = Incorrect
		stage.Error = "candidate snapshot changed during execution"
		if watchErr != nil {
			stage.Status = InfraError
			stage.Error = "read snapshot mutation events: " + watchErr.Error()
		}
		return
	}
	if ctx.Err() != nil {
		if stage.Status == Correct {
			stage.Status = contextStatus(ctx)
			stage.Error = ctx.Err().Error()
		}
		return
	}
	digest, err := treeDigest(ctx, snapshot, true)
	if err == nil && digest == baseline {
		return
	}
	if stage.Status != Correct {
		return
	}
	if ctx.Err() != nil {
		stage.Status = contextStatus(ctx)
		stage.Error = ctx.Err().Error()
		return
	}
	stage.Status = Incorrect
	stage.Error = "candidate snapshot changed during execution"
	if err != nil {
		stage.Error += ": " + err.Error()
	}
}

func contextStatus(ctx context.Context) string {
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return Timeout
	}
	return InfraError
}
