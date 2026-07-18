// Command tessercheck runs the go/analysis-based domain-construction checkers.
// It works as a standalone driver (tessercheck ./...) and as a go vet tool
// (go vet -vettool=$(command -v tessercheck) ./...). Editor integration goes
// through the golangci-lint module plugin (gclplugin/), not gopls — gopls only
// runs analyzers compiled into it (see README "Editor integration").
//
// Per-analyzer flags are namespaced, e.g.:
//
//	tessercheck -mustnew.exclude=Ledger,Transaction -vofields.exclude=Ledger ./...
package main

import (
	"os"

	"golang.org/x/tools/go/analysis/multichecker"

	"github.com/verocorp/tesser-build/internal/analyzers"
)

func main() {
	// The starter-config generator is a separate mode, outside the
	// go/analysis multichecker.
	if maybeGenExcludes(os.Args) {
		return
	}
	multichecker.Main(analyzers.All...)
}
