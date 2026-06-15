import os
import shutil
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)

MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 262144
MNT_DETACH = 2
SYS_PIVOT_ROOT = 155

def syscall_mount(src, tgt, fstype, flags, data):
    src_bytes = src.encode() if src else None
    tgt_bytes = tgt.encode()
    fstype_bytes = fstype.encode() if fstype else None
    data_bytes = data.encode() if data else None

    result = libc.mount(src_bytes, tgt_bytes, fstype_bytes, flags, data_bytes)
    
    if result < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"Mount failed on {tgt} ({os.strerror(errno)})")

def setup_container_fs(run_dir):
    syscall_mount("none", "/", None, MS_REC | MS_PRIVATE, None)

    base_image = os.path.abspath("rootfs")
    merged_dir = os.path.join(run_dir, "merged")

    # Step 1: Create overlay dirs and mount FIRST
    for d in ["upper", "work", "merged"]:
        os.makedirs(os.path.join(run_dir, d), exist_ok=True)

    opts = (
        f"lowerdir={base_image},"
        f"upperdir={os.path.join(run_dir, 'upper')},"
        f"workdir={os.path.join(run_dir, 'work')}"
    )
    syscall_mount("overlay", merged_dir, "overlay", 0, opts)

    # Step 2: Inject DNS AFTER overlay is mounted, into merged_dir
    # This is the critical fix — the container pivots INTO merged_dir,
    # so /etc/resolv.conf must exist there, not in run_dir.
    resolv_target = os.path.join(merged_dir, "etc", "resolv.conf")
    os.makedirs(os.path.dirname(resolv_target), exist_ok=True)
    if os.path.lexists(resolv_target):
        os.remove(resolv_target)  # handles broken symlinks (common in Ubuntu base images)
    with open(resolv_target, "w") as f:
        f.write("nameserver 8.8.8.8\n")
        f.write("nameserver 1.1.1.1\n")

    # Step 3: Bind-mount merged_dir onto itself (pivot_root requirement)
    syscall_mount(merged_dir, merged_dir, None, MS_BIND, None)

    # Step 4: Bind-mount workspace into container's /var/www
    host_workspace = os.path.abspath("workspace")
    container_workspace = os.path.join(merged_dir, "var/www")
    os.makedirs(host_workspace, exist_ok=True)
    os.makedirs(container_workspace, exist_ok=True)
    syscall_mount(host_workspace, container_workspace, None, MS_BIND | MS_REC, None)

    # Step 5: Mount /proc
    proc_path = os.path.join(merged_dir, "proc")
    os.makedirs(proc_path, exist_ok=True)
    syscall_mount("proc", proc_path, "proc", 0, None)

    # Step 6: pivot_root
    old_root = os.path.join(merged_dir, "old_root")
    os.makedirs(old_root, exist_ok=True)
    os.chdir(merged_dir)

    if libc.syscall(SYS_PIVOT_ROOT, b".", b"old_root") < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"pivot_root failed: {os.strerror(errno)}")

    os.chdir("/")

    if libc.umount2(b"/old_root", MNT_DETACH) < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"umount2 failed: {os.strerror(errno)}")

    os.rmdir("/old_root")
