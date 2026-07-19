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
	"go/token"
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
	"//line ",
	"/*line ",
	"//nolint",
	"//export ",
	"//extern ",
	"//sys",
	"// +build",
}

// goDirective is the `//go:name` family. A space after the colon is never a
// real directive — `//go: prose` must not ride the exemption.
var goDirective = regexp.MustCompile(`^//go:\S`)

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
	return goDirective.MatchString(text) || tbMarker.MatchString(text)
}

func run(pass *analysis.Pass) (any, error) {
	for _, f := range pass.Files {
		if ast.IsGenerated(f) {
			continue
		}
		preambles := cgoPreambles(f)
		for _, group := range f.Comments {
			if preambles[group] {
				continue
			}
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

// cgoPreambles returns the comment groups the Go toolchain itself consumes:
// the preamble attached to an `import "C"` declaration. Those comments are
// code, not prose — banning them would ban cgo.
func cgoPreambles(f *ast.File) map[*ast.CommentGroup]bool {
	exempt := map[*ast.CommentGroup]bool{}
	for _, decl := range f.Decls {
		gen, ok := decl.(*ast.GenDecl)
		if !ok || gen.Tok != token.IMPORT {
			continue
		}
		for _, spec := range gen.Specs {
			imp, ok := spec.(*ast.ImportSpec)
			if !ok || imp.Path == nil || imp.Path.Value != `"C"` {
				continue
			}
			if gen.Doc != nil {
				exempt[gen.Doc] = true
			}
			if imp.Doc != nil {
				exempt[imp.Doc] = true
			}
		}
	}
	return exempt
}
