package experimentcorpus

import (
	"os"
	"path/filepath"
	"testing"
)

func TestOutputRootAcceptsOnlyEmptyDirectories(t *testing.T) {
	base := t.TempDir()
	for _, path := range []string{base, filepath.Join(base, "new")} {
		root, err := outputRoot(path)
		if err != nil {
			t.Fatal(err)
		}
		if err := root.Close(); err != nil {
			t.Fatal(err)
		}
	}
	if root, err := outputRoot(base); err == nil {
		root.Close()
		t.Fatal("accepted a directory containing a subdirectory")
	}
}

func TestOutputRootRejectsLinksAndFilesWithoutWriting(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "target")
	if err := os.Mkdir(target, 0o755); err != nil {
		t.Fatal(err)
	}
	link, dangling := filepath.Join(base, "link"), filepath.Join(base, "dangling")
	for from, to := range map[string]string{link: target, dangling: filepath.Join(base, "absent")} {
		if err := os.Symlink(to, from); err != nil {
			t.Fatal(err)
		}
	}
	file := filepath.Join(base, "file")
	if err := os.WriteFile(file, []byte("original"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{"", link, filepath.Join(link, "child"), dangling, file, filepath.Join(file, "child"), filepath.Join(base, "missing", "child")} {
		if root, err := outputRoot(path); err == nil {
			root.Close()
			t.Errorf("accepted %q", path)
		}
	}
	entries, err := os.ReadDir(target)
	if err != nil || len(entries) != 0 {
		t.Fatalf("symlink target modified: %v %v", entries, err)
	}
	content, err := os.ReadFile(file)
	if err != nil || string(content) != "original" {
		t.Fatalf("file modified: %s %v", content, err)
	}
}

func TestOutputRootRejectsSymlinkedContents(t *testing.T) {
	base := t.TempDir()
	dir := filepath.Join(base, "output")
	if err := os.Mkdir(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(base, "absent"), filepath.Join(dir, "application.py")); err != nil {
		t.Fatal(err)
	}
	if root, err := outputRoot(dir); err == nil {
		root.Close()
		t.Fatal("accepted directory containing a dangling link")
	}
	if _, err := os.Lstat(filepath.Join(base, "absent")); !os.IsNotExist(err) {
		t.Fatalf("created symlink target: %v", err)
	}
}
