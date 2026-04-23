package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	excludeFlag := flag.String("exclude", "", "comma-separated type names exempt from the Test*_Equality requirement (typically aggregates, entities, and types with non-comparable fields)")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [--exclude=Type1,Type2] [path]\n", os.Args[0])
		fmt.Fprintln(os.Stderr, "\nChecks that every value-object type X has a corresponding Test*_Equality")
		fmt.Fprintln(os.Stderr, "test function covering equality semantics.")
		flag.PrintDefaults()
	}
	flag.Parse()

	excluded := parseExcludes(*excludeFlag)

	root := "."
	if flag.NArg() > 0 {
		root = flag.Arg(0)
	}

	var allViolations []Violation

	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			return nil
		}
		base := filepath.Base(path)
		if base != "." && (base[0] == '.' || base == "vendor") {
			return filepath.SkipDir
		}

		matches, _ := filepath.Glob(filepath.Join(path, "*.go"))
		if len(matches) == 0 {
			return nil
		}

		violations, checkErr := CheckPackageDir(path, excluded)
		if checkErr != nil {
			return checkErr
		}
		allViolations = append(allViolations, violations...)
		return nil
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(2)
	}

	for _, v := range allViolations {
		fmt.Println(v)
	}

	if len(allViolations) == 0 {
		fmt.Println("PASS: All VOs have Test*_Equality coverage.")
		return
	}
	fmt.Printf("\nFAIL: %d VO(s) missing Test*_Equality coverage.\n", len(allViolations))
	os.Exit(1)
}

func parseExcludes(s string) map[string]bool {
	out := map[string]bool{}
	for _, name := range strings.Split(s, ",") {
		name = strings.TrimSpace(name)
		if name == "" {
			continue
		}
		out[name] = true
	}
	return out
}
