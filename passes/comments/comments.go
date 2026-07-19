// Package comments enforces the comments norm (v0, skills/tesser-build/comments.md):
// constructed-app code carries no comments — no line comments, no block
// comments, no doc comments. Machine directives are exempt (they are
// instructions to tools, not prose): //go: directives, build constraints,
// //line, //nolint, //export, the tb-cell/tb-status/tb-allow-missing roadmap
// marker grammar, and generated-file headers (generated files are skipped
// wholesale). Carve-outs beyond the directive ledger are added only from
// discovered evidence — extend the ledger in comments.md and here in the
// same change.
package comments

import (
	"go/ast"
	"regexp"
	"strings"

	"golang.org/x/tools/go/analysis"
)

// Analyzer reports every non-directive comment.
var Analyzer = &analysis.Analyzer{
	Name: "comments",
	Doc:  "code comments are banned (v0 zero-comment norm); machine directives exempt",
	Run:  run,
}

// directivePrefixes is the v0 exemption ledger for line comments. A comment
// is exempt iff it starts with one of these — trailing text rides along
// (a //nolint's reason is part of the directive).
var directivePrefixes = []string{
	"//go:",
	"//line ",
	"//nolint",
	"//export ",
	"//extern ",
	"//sys",
	"// +build",
}

// tbMarker is the roadmap annotation grammar (docs/skill-authoring.md). The
// pattern is spelled as an alternation so this source line does not itself
// scan as a marker.
var tbMarker = regexp.MustCompile(`^// ?tb-(cell|status|allow-missing):`)

func isDirective(text string) bool {
	for _, p := range directivePrefixes {
		if strings.HasPrefix(text, p) {
			return true
		}
	}
	return tbMarker.MatchString(text)
}

func run(pass *analysis.Pass) (any, error) {
	for _, f := range pass.Files {
		if ast.IsGenerated(f) {
			continue
		}
		for _, group := range f.Comments {
			for _, c := range group.List {
				if isDirective(c.Text) {
					continue
				}
				pass.Reportf(c.Pos(), "code comment is banned (zero-comment norm v0); delete it — if it states a real constraint, that belongs in the doc layer (skills/tesser-build/comments.md)")
			}
		}
	}
	return nil, nil
}
