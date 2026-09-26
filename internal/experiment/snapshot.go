package experiment

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"syscall"
)

func ContainsPath(directory, path string) bool {
	relative, err := filepath.Rel(directory, path)
	return err == nil && relative != ".." && !filepath.IsAbs(relative) && !startsWithParent(relative)
}

func startsWithParent(path string) bool {
	return len(path) > 3 && path[:3] == ".."+string(filepath.Separator)
}

func candidatePath(path string) (string, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return "", err
	}
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("candidate must be a real directory, not a symlink")
	}
	return filepath.EvalSymlinks(path)
}

func treeDigest(ctx context.Context, root string, metadata bool) (string, error) {
	hash := sha256.New()
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if err := validateEntry(path, info); err != nil {
			return err
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		name := []byte(filepath.ToSlash(relative))
		binary.Write(hash, binary.BigEndian, uint64(len(name)))
		hash.Write(name)
		binary.Write(hash, binary.BigEndian, uint32(info.Mode()))
		if metadata {
			binary.Write(hash, binary.BigEndian, info.ModTime().UnixNano())
		}
		if info.IsDir() {
			return nil
		}
		binary.Write(hash, binary.BigEndian, uint64(info.Size()))
		file, err := os.Open(path)
		if err != nil {
			return err
		}
		defer file.Close()
		_, err = io.Copy(hash, contextReader{ctx: ctx, reader: file})
		return err
	})
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

type contextReader struct {
	ctx    context.Context
	reader io.Reader
}

func (reader contextReader) Read(buffer []byte) (int, error) {
	if err := reader.ctx.Err(); err != nil {
		return 0, err
	}
	return reader.reader.Read(buffer)
}

func validateEntry(path string, info fs.FileInfo) error {
	if !info.Mode().IsRegular() && !info.IsDir() {
		return fmt.Errorf("candidate contains symlink or special file: %s", path)
	}
	if info.Mode().IsRegular() {
		stat, ok := info.Sys().(*syscall.Stat_t)
		if !ok || stat.Nlink > 1 {
			return fmt.Errorf("candidate contains hard-linked file: %s", path)
		}
	}
	return nil
}

func copyTree(ctx context.Context, source, destination string) error {
	var directories []string
	err := filepath.WalkDir(source, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if err := validateEntry(path, info); err != nil {
			return err
		}
		relative, err := filepath.Rel(source, path)
		if err != nil {
			return err
		}
		target := filepath.Join(destination, relative)
		if info.IsDir() {
			directories = append(directories, relative)
			return os.MkdirAll(target, 0700)
		}
		input, err := os.Open(path)
		if err != nil {
			return err
		}
		defer input.Close()
		output, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if err != nil {
			return err
		}
		_, copyErr := io.Copy(output, contextReader{ctx: ctx, reader: input})
		closeErr := output.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
		if err := os.Chmod(target, info.Mode().Perm()); err != nil {
			return err
		}
		return os.Chtimes(target, info.ModTime(), info.ModTime())
	})
	if err != nil {
		return err
	}
	for index := len(directories) - 1; index >= 0; index-- {
		relative := directories[index]
		info, err := os.Stat(filepath.Join(source, relative))
		if err != nil {
			return err
		}
		if err := os.Chmod(filepath.Join(destination, relative), info.Mode().Perm()); err != nil {
			return err
		}
		if err := os.Chtimes(filepath.Join(destination, relative), info.ModTime(), info.ModTime()); err != nil {
			return err
		}
	}
	return nil
}

func removeSnapshot(path string) {
	filepath.WalkDir(path, func(name string, entry fs.DirEntry, err error) error {
		if err == nil && entry.IsDir() {
			os.Chmod(name, 0700)
		}
		return nil
	})
	os.RemoveAll(path)
}
