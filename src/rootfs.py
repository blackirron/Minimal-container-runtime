import os
import tempfile
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)

MS_BIND = 4096
MNT_DETACH = 2
SYS_PIVOT_ROOT = 155

def mount_syscall(source, target, fs_type, flags, data):    #to conv strings to raw bytes for use in c  
	res = libc.mount(
		source.encode() if source else None,
		target.encode(),
		fs_type.encode() if fs_type else None,
		flags,
		data.encode() if data else None
	)
	if res < 0:
		errno = ctypes.get_errno()
		raise OSError(errno, f"mount failes on {target}: {os.strerror(errno)}")

def umount2_syscall(target, flags):
    res = libc.umount2(target.encode(), flags)
    if res < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"umount2 failed on {target}: {os.strerror(errno)}")

def setup_rootfs():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_image = os.path.join(script_dir, "..", "rootfs")
    if not os.path.exists(base_image):
        raise FileNotFoundError(f"Base rootfs not found at {base_image}")
    run_dir = tempfile.mkdtemp(prefix="mdocker-")
    upper_dir = os.path.join(run_dir, "upper")
    work_dir = os.path.join(run_dir, "work")
    merged_dir = os.path.join(run_dir, "merged")

    for d in [upper_dir, work_dir, merged_dir]:
        os.mkdir(d)
    opts = f"lowerdir={base_image},upperdir={upper_dir},workdir={work_dir}"
    mount_syscall("overlay", merged_dir, "overlay", 0, opts)
    mount_syscall(merged_dir, merged_dir, None, MS_BIND, None)
    old_root = os.path.join(merged_dir, "old_root")
    os.mkdir(old_root)

    os.chdir(merged_dir)
    if libc.syscall(SYS_PIVOT_ROOT, b".", b"old_root") < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"pivot_root failed: {os.strerror(errno)}")

    os.chdir("/")
    umount2_syscall("/old_root", MNT_DETACH)
    os.rmdir("/old_root")
