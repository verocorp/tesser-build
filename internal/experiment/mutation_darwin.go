package experiment

import (
	"context"
	"io/fs"
	"path/filepath"
	"syscall"
)

type mutationWatch struct {
	fd    int
	files []int
}

func watchMutations(ctx context.Context, root string) (*mutationWatch, error) {
	fd, err := syscall.Kqueue()
	if err != nil {
		return nil, err
	}
	syscall.CloseOnExec(fd)
	watch := &mutationWatch{fd: fd}
	err = filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		file, err := syscall.Open(path, syscall.O_EVTONLY|syscall.O_CLOEXEC, 0)
		if err != nil {
			return err
		}
		watch.files = append(watch.files, file)
		event := syscall.Kevent_t{Ident: uint64(file), Filter: syscall.EVFILT_VNODE, Flags: syscall.EV_ADD | syscall.EV_CLEAR, Fflags: syscall.NOTE_WRITE | syscall.NOTE_EXTEND | syscall.NOTE_ATTRIB | syscall.NOTE_LINK | syscall.NOTE_RENAME | syscall.NOTE_DELETE | syscall.NOTE_REVOKE}
		_, err = syscall.Kevent(fd, []syscall.Kevent_t{event}, nil, nil)
		return err
	})
	if err != nil {
		watch.close()
		return nil, err
	}
	return watch, nil
}

func (watch *mutationWatch) changed() (bool, error) {
	var events [1]syscall.Kevent_t
	for {
		count, err := syscall.Kevent(watch.fd, nil, events[:], &syscall.Timespec{})
		if err == syscall.EINTR {
			continue
		}
		return count > 0, err
	}
}

func (watch *mutationWatch) close() error {
	for _, file := range watch.files {
		syscall.Close(file)
	}
	return syscall.Close(watch.fd)
}
