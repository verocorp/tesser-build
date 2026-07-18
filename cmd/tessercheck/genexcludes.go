package main

import (
	"fmt"
	"os"
	"time"

	"golang.org/x/tools/go/packages"

	"github.com/verocorp/tesser-build/internal/genexclude"
	"github.com/verocorp/tesser-build/internal/voscan"
)

// maybeGenExcludes handles `tessercheck -gen-excludes [packages...]`, the
// starter-config generator. It lives outside the go/analysis multichecker, so
// main dispatches to it before handing off. It returns true when it handled the
// invocation.
//
// It never clobbers an existing .tesser-build.yaml — that file is human-curated, and
// silently overwriting it could drop a hand-added exclusion (re-introducing the
// silent gap the toolkit exists to prevent). On first run it writes the file;
// when one already exists it prints the regenerated content to stdout for the
// user to diff in.
func maybeGenExcludes(args []string) bool {
	if len(args) < 2 || args[1] != "-gen-excludes" {
		return false
	}
	patterns := args[2:]
	if len(patterns) == 0 {
		patterns = []string{"./..."}
	}

	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedTypes | packages.NeedSyntax |
			packages.NeedTypesInfo | packages.NeedDeps | packages.NeedImports,
	}
	pkgs, err := packages.Load(cfg, patterns...)
	if err != nil {
		fmt.Fprintf(os.Stderr, "tessercheck -gen-excludes: %v\n", err)
		os.Exit(2)
	}
	if packages.PrintErrors(pkgs) > 0 {
		os.Exit(2)
	}

	entries := genexclude.Classify(pkgs)
	out := genexclude.Render(entries, time.Now().Format("2006-01-02"))

	if _, err := os.Stat(voscan.ConfigName); err == nil {
		fmt.Fprintf(os.Stderr, "%s already exists — not overwriting. Regenerated content below; diff in by hand:\n\n", voscan.ConfigName)
		fmt.Print(out)
		return true
	}
	if err := os.WriteFile(voscan.ConfigName, []byte(out), 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "tessercheck -gen-excludes: writing %s: %v\n", voscan.ConfigName, err)
		os.Exit(2)
	}
	fmt.Fprintf(os.Stderr, "wrote %s with %d exclude(s); review before committing.\n", voscan.ConfigName, len(entries))
	return true
}
