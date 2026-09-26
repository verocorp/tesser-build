package experiment

import (
	"context"
	"io/fs"
	"path/filepath"
	"syscall"
)

type mutationWatch struct {
	fd int
}

func watchMutations(ctx context.Context, root string) (*mutationWatch, error) {
	fd, err := syscall.InotifyInit1(syscall.IN_NONBLOCK | syscall.IN_CLOEXEC)
	if err != nil {
		return nil, err
	}
	watch := &mutationWatch{fd: fd}
	err = filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		_, err := syscall.InotifyAddWatch(fd, path, syscall.IN_MODIFY|syscall.IN_ATTRIB|syscall.IN_CREATE|syscall.IN_DELETE|syscall.IN_DELETE_SELF|syscall.IN_MOVE_SELF|syscall.IN_MOVED_FROM|syscall.IN_MOVED_TO)
		return err
	})
	if err != nil {
		watch.close()
		return nil, err
	}
	return watch, nil
}

func (watch *mutationWatch) changed() (bool, error) {
	var events [4096]byte
	for {
		count, err := syscall.Read(watch.fd, events[:])
		if err == syscall.EINTR {
			continue
		}
		if err == syscall.EAGAIN {
			return false, nil
		}
		return count > 0, err
	}
}

func (watch *mutationWatch) close() error {
	return syscall.Close(watch.fd)
}
