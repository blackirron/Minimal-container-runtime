import os
import ctypes

libc = ctypes.CDLL("libc.so.6", use_errno=True)
ROOTFS = os.path.abspath("../rootfs")

# Direct x86_64 Linux kernel architecture system call ID
SYS_PIVOT_ROOT = 155

def setup_rootfs():
    # 1. Bind mount rootfs to itself to turn it into an official mount point (MS_BIND = 4096)
    if libc.mount(ROOTFS.encode(), ROOTFS.encode(), None, 4096, None) != 0:
        raise RuntimeError(f"Bind mount failed: {os.strerror(ctypes.get_errno())}")

    # 2. Create the escape-proof anchor point for the old host filesystem
    old_root = os.path.join(ROOTFS, "old_root")
    os.makedirs(old_root, exist_ok=True)

    # 3. Direct system call invocation to securely swap filesystems
    if libc.syscall(SYS_PIVOT_ROOT, ROOTFS.encode(), old_root.encode()) != 0:
        raise RuntimeError(f"pivot_root syscall failed: {os.strerror(ctypes.get_errno())}")

    # 4. Snap the working context to the new isolated root filesystem
    os.chdir("/")

    # 5. Lazily unmount the host root to completely wipe its visibility (MNT_DETACH = 2)
    if libc.umount2(b"/old_root", 2) != 0:
        raise RuntimeError(f"Detaching old root failed: {os.strerror(ctypes.get_errno())}")
    
    # 6. Clean up the temporary tracking directory
    os.rmdir("/old_root")
