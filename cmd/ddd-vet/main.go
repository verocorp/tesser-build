// Command ddd-vet runs the go/analysis-based DDD checkers. It works as a
// standalone driver (ddd-vet ./...) and as a go vet tool
// (go vet -vettool=$(command -v ddd-vet) ./...), which also lights the
// checkers up in editors through gopls.
//
// Per-analyzer flags are namespaced, e.g.:
//
//	ddd-vet -mustnew.exclude=Ledger,Transaction -vofields.exclude=Ledger ./...
package main

import (
	"os"

	"golang.org/x/tools/go/analysis/multichecker"

	"github.com/chrisconley/go-ddd/passes/mustnew"
	"github.com/chrisconley/go-ddd/passes/vofields"
)

func main() {
	// The starter-config generator is a separate mode, outside the
	// go/analysis multichecker.
	if maybeGenExcludes(os.Args) {
		return
	}
	multichecker.Main(
		mustnew.Analyzer,
		vofields.Analyzer,
	)
}
