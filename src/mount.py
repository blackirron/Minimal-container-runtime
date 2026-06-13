import os
import ctypes

libc = ctypes.CDLL("libc.so.6", use_errno=True)

def setup_mounts():
    os.makedirs("/proc", exist_ok=True)
    
    result = libc.mount(b"proc", b"/proc", b"proc", 0, None)
    
    if result != 0:
        err = ctypes.get_errno()
        raise RuntimeError(f"Failed to mount /proc. Errno: {err} ({os.strerror(err)})")
