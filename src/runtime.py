import os, sys
from namespaces import setup_namespaces
from rootfs import setup_rootfs
from cgroups import setup_cgroups
from mount import setup_mounts
from network import setup_network

def run_container(command):
    if os.getenv("CONTAINER_INIT") == "1":
        setup_rootfs()
        setup_mounts()
        os.execvp(command[0], command) 

    if (pid := os.fork()) == 0:
        setup_namespaces()
        if (child_pid := os.fork()) == 0:
            os.environ["CONTAINER_INIT"] = "1"
            os.execv("/proc/self/exe", [sys.executable] + sys.argv)
        
        os.waitpid(child_pid, 0)
        sys.exit(0)

    setup_cgroups(pid)
    setup_network(pid)
    os.waitpid(pid, 0)
