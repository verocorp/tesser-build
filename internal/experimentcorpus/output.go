package experimentcorpus

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func outputRoot(path string) (*os.Root, error) {
	if path == "" {
		return nil, errors.New("out is required")
	}
	absolute, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	anchor := filepath.VolumeName(absolute) + string(filepath.Separator)
	root, err := os.OpenRoot(anchor)
	if err != nil {
		return nil, err
	}
	parts := strings.Split(strings.TrimPrefix(absolute, anchor), string(filepath.Separator))
	for i, part := range parts {
		if part == "" {
			continue
		}
		info, err := root.Lstat(part)
		if errors.Is(err, os.ErrNotExist) && i == len(parts)-1 {
			if err := root.Mkdir(part, 0o755); err != nil {
				root.Close()
				return nil, err
			}
			info, err = root.Lstat(part)
		}
		if err != nil {
			root.Close()
			return nil, err
		}
		if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			root.Close()
			return nil, fmt.Errorf("output path must contain only directories, not symlinks: %s", part)
		}
		child, err := root.OpenRoot(part)
		if err != nil {
			root.Close()
			return nil, err
		}
		opened, statErr := child.Stat(".")
		current, linkErr := root.Lstat(part)
		root.Close()
		if statErr != nil || linkErr != nil {
			child.Close()
			return nil, errors.Join(statErr, linkErr)
		}
		if current.Mode()&os.ModeSymlink != 0 || !os.SameFile(info, opened) || !os.SameFile(current, opened) {
			child.Close()
			return nil, errors.New("output path changed while opening")
		}
		root = child
	}
	dir, err := root.Open(".")
	if err != nil {
		root.Close()
		return nil, err
	}
	entries, readErr := dir.ReadDir(-1)
	closeErr := dir.Close()
	if err := errors.Join(readErr, closeErr); err != nil {
		root.Close()
		return nil, err
	}
	if len(entries) != 0 {
		root.Close()
		return nil, errors.New("output directory must be empty")
	}
	return root, nil
}
