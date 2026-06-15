import socket
import ctypes

CLONE_NEWUTS = 0x04000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNS  = 0x00020000
CLONE_NEWNET = 0x40000000

libc = ctypes.CDLL("libc.so.6")

def setup_namespaces():
    # Unshare UTS, PID, mount, and network namespaces in one call
    libc.unshare(CLONE_NEWUTS | CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET)
    socket.sethostname("container")  # blank hostname was causing the empty ":/#" prompt
