import os
import ctypes

libc = ctypes.CDLL("libc.so.6", use_errno=True)
ROOTFS = os.path.abspath("../rootfs")

SYS_PIVOT_ROOT = 155

def setup_rootfs():
    if libc.mount(ROOTFS.encode(), ROOTFS.encode(), None, 4096, None) != 0:
        raise RuntimeError(f"Bind mount failed: {os.strerror(ctypes.get_errno())}")

    old_root = os.path.join(ROOTFS, "old_root")
    os.makedirs(old_root, exist_ok=True)

    if libc.syscall(SYS_PIVOT_ROOT, ROOTFS.encode(), old_root.encode()) != 0:
        raise RuntimeError(f"pivot_root syscall failed: {os.strerror(ctypes.get_errno())}")

    os.chdir("/")

    if libc.umount2(b"/old_root", 2) != 0:
        raise RuntimeError(f"Detaching old root failed: {os.strerror(ctypes.get_errno())}")
    
    os.rmdir("/old_root")
