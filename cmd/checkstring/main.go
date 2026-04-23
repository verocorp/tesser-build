package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	root := "."
	if len(os.Args) > 1 {
		root = os.Args[1]
	}

	var allViolations []Violation

	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			return nil
		}
		// Skip hidden directories and vendor.
		base := filepath.Base(path)
		if base != "." && (base[0] == '.' || base == "vendor") {
			return filepath.SkipDir
		}

		// Only scan directories that contain test files.
		matches, _ := filepath.Glob(filepath.Join(path, "*_test.go"))
		if len(matches) == 0 {
			return nil
		}

		violations, checkErr := CheckPackageDir(path)
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
		fmt.Println("PASS: No .String() calls outside Test*_String accessor tests.")
	} else {
		fmt.Printf("\nFAIL: %d .String() call(s) outside accessor tests.\n", len(allViolations))
		fmt.Println("Use VO-level comparison, typed assertions, string literals, or fmt-verb formatting instead. See llm-tools/domain-objects.md step 9.")
		os.Exit(1)
	}
}
