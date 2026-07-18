// Command analyzers-json dumps the analyzers.All registry as JSON on stdout —
// the Go side of the cross-language bridge the roadmap generator
// (roadmap/generate.py) consumes via subprocess. Same bridge shape as
// rationale/coverage_test.go keying off the registry, now emitting instead of
// only validating. Any failure must exit nonzero: the generator treats a dead
// bridge as a loud error, never an empty checker column.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/verocorp/tesser-build/internal/analyzers"
)

type analyzerInfo struct {
	Name string `json:"name"`
	Doc  string `json:"doc"`
}

func main() {
	infos := make([]analyzerInfo, 0, len(analyzers.All))
	for _, a := range analyzers.All {
		infos = append(infos, analyzerInfo{Name: a.Name, Doc: a.Doc})
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(infos); err != nil {
		fmt.Fprintf(os.Stderr, "analyzers-json: %v\n", err)
		os.Exit(1)
	}
}
