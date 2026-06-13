import socket
import ctypes

CLONE_NEWUTS  = 0x04000000
CLONE_NEWPID  = 0x20000000
CLONE_NEWNS   = 0x00020000

MS_REC        = 16384
MS_PRIVATE    = 262144

libc = ctypes.CDLL("libc.so.6")

def setup_namespaces():
    libc.unshare(CLONE_NEWUTS | CLONE_NEWPID | CLONE_NEWNS)
    libc.mount(b"none", b"/", None, MS_REC | MS_PRIVATE, None)
    socket.sethostname(b"")
