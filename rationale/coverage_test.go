package changeability_test

import (
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"github.com/verocorp/go-ddd/internal/analyzers"
)

// TestCoverageMatrix_NoSilentGaps keeps coverage.md honest: every analyzer
// ddd-vet ships (internal/analyzers.All) must appear in the matrix, and every
// Test* the matrix names must exist in this package. It tolerates the ❌/⚠️ rows
// by design (the rationale is broader than the enforcement, and some analyzers
// enforce a rubric rule whose demo is still pending); it forbids a SILENT gap —
// a shipping analyzer missing from the matrix, or a dangling test reference that
// rotted.
func TestCoverageMatrix_NoSilentGaps(t *testing.T) {
	matrix, err := os.ReadFile("coverage.md")
	if err != nil {
		t.Fatalf("read coverage.md: %v", err)
	}
	content := string(matrix)

	// 1. Every analyzer ddd-vet ships is named in the matrix. Keyed off the
	// analyzers.All registry — not the cmd/check* dirs — so the guard stays live
	// after the standalone walkers are removed.
	for _, a := range analyzers.All {
		if !strings.Contains(content, a.Name) {
			t.Errorf("analyzer %q has no row in coverage.md (silent gap)", a.Name)
		}
	}

	// 2. Every concrete Test* the matrix references actually exists here.
	// (Patterns like "Test*_Equality" carry an asterisk and are not matched.)
	var src strings.Builder
	testFiles, _ := filepath.Glob("*_test.go")
	// Also the changeability arms' tests (a separate matrix dimension): the
	// coverage.md "Changeability arms" row names them, so they must resolve here.
	anchorTests, _ := filepath.Glob(filepath.Join("changeability", "anchor", "*_test.go"))
	nooutwardTests, _ := filepath.Glob(filepath.Join("changeability", "nooutward", "*_test.go"))
	armTests := append(anchorTests, nooutwardTests...)
	for _, f := range append(testFiles, armTests...) {
		b, _ := os.ReadFile(f)
		src.Write(b)
	}
	srcStr := src.String()

	for _, name := range regexp.MustCompile(`Test[A-Za-z0-9_]+`).FindAllString(content, -1) {
		if !strings.Contains(srcStr, "func "+name+"(") {
			t.Errorf("coverage.md references %q but no such test exists (dangling reference)", name)
		}
	}
}

// TestSkillMaterializationAnchors is the structural half of the skill-matrix
// contract (design v2, H6): every `file.md#anchor` the skill-materializations
// table names must resolve to a real heading in that file under skills/ddd/. It
// catches a renamed heading, a mistyped anchor, or a routeless concept file —
// the silent drift the manual matrix invites once the seam concepts expand it.
// It does NOT check semantic agreement between renderings; that stays human
// review. Pulled forward from the rationale phase because the v2 seam content
// (application services, repositories) has no analyzer net of its own.
func TestSkillMaterializationAnchors(t *testing.T) {
	matrix, err := os.ReadFile("coverage.md")
	if err != nil {
		t.Fatalf("read coverage.md: %v", err)
	}
	content := string(matrix)

	// Scope to the skill-materializations section so unrelated file#frag
	// mentions elsewhere in the doc don't get treated as matrix anchors.
	_, section, found := strings.Cut(content, "## Skill materializations")
	if !found {
		t.Fatal("coverage.md has no '## Skill materializations' section")
	}
	if before, _, ok := strings.Cut(section, "\n## "); ok {
		section = before
	}

	skillDir := filepath.Join("..", "skills", "ddd")
	anchorsByFile := map[string]map[string]bool{}
	loadAnchors := func(file string) (map[string]bool, error) {
		if a, ok := anchorsByFile[file]; ok {
			return a, nil
		}
		b, err := os.ReadFile(filepath.Join(skillDir, file))
		if err != nil {
			return nil, err
		}
		set := map[string]bool{}
		explicit := regexp.MustCompile(`\{#([a-z0-9-]+)\}`)
		inFence := false
		for line := range strings.SplitSeq(string(b), "\n") {
			if strings.HasPrefix(strings.TrimSpace(line), "```") {
				inFence = !inFence // ignore '#' comments inside code blocks
				continue
			}
			if inFence || !regexp.MustCompile(`^#{1,6}\s`).MatchString(line) {
				continue
			}
			text := strings.TrimLeft(line, "# ")
			if m := explicit.FindStringSubmatch(text); m != nil {
				set[m[1]] = true
				text = explicit.ReplaceAllString(text, "")
			}
			set[slugifyHeading(text)] = true
		}
		anchorsByFile[file] = set
		return set, nil
	}

	refRe := regexp.MustCompile(`([a-z0-9-]+\.md)#([a-z0-9-]+)`)
	seen := map[string]bool{}
	for _, m := range refRe.FindAllStringSubmatch(section, -1) {
		ref, file, anchor := m[0], m[1], m[2]
		if seen[ref] {
			continue
		}
		seen[ref] = true
		set, err := loadAnchors(file)
		if err != nil {
			t.Errorf("matrix references %s but skills/ddd/%s: %v", ref, file, err)
			continue
		}
		if !set[anchor] {
			t.Errorf("matrix references %s but no heading in skills/ddd/%s produces anchor #%s", ref, file, anchor)
		}
	}
	if len(seen) == 0 {
		t.Error("no file.md#anchor references found in the skill-materializations section")
	}
}

// slugifyHeading approximates GitHub's heading-anchor algorithm: lowercase,
// drop punctuation, keep word chars and hyphens, spaces become hyphens.
func slugifyHeading(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= '0' && r <= '9', r == '_', r == '-':
			b.WriteRune(r)
		case r == ' ':
			b.WriteRune('-')
		}
	}
	return b.String()
}
