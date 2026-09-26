package main

import (
	"flag"
	"fmt"
	"io"
	"os"

	"github.com/verocorp/tesser-build/internal/experimentcorpus"
)

func run(args []string, stderr io.Writer) int {
	flags := flag.NewFlagSet("tesser-corpus", flag.ContinueOnError)
	flags.SetOutput(stderr)
	family := flags.String("family", "", "reserving-inventory or transferring-funds")
	variant := flags.String("variant", "", "structured or scattered")
	seed := flags.Int64("seed", 0, "deterministic implementation seed")
	out := flags.String("out", "", "new or empty output directory (parent must exist)")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() != 0 {
		fmt.Fprintln(stderr, "tesser-corpus: unexpected positional arguments")
		return 2
	}
	if err := experimentcorpus.Generate(experimentcorpus.Options{Family: *family, Variant: *variant, Seed: *seed, Out: *out}); err != nil {
		fmt.Fprintf(stderr, "tesser-corpus: %v\n", err)
		return 1
	}
	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stderr))
}
