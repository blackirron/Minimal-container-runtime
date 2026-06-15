import os
import sys
import subprocess
import shutil
import tempfile

from namespaces import setup_namespaces
from rootfs import setup_container_fs
from cgroups import setup_cgroups, teardown_cgroups
from network import setup_network

def preflight_check():
    if subprocess.run("ip link show appnet &>/dev/null", shell=True).returncode != 0:
        print("[SETUP] Running host setup...")
        subprocess.run(["python3", "src/setup_host.py"], check=True)

def run_container(command):
    if os.getenv("CONTAINER_INIT") == "1":
        setup_container_fs(os.getenv("RUN_DIR"))
        os.execvp(command[0], command)

    preflight_check()

    run_dir = tempfile.mkdtemp(prefix="mdocker-")
    pid = os.fork()

    if pid == 0:
        setup_namespaces()
        if (child_pid := os.fork()) == 0:
            os.environ["CONTAINER_INIT"] = "1"
            os.environ["RUN_DIR"] = run_dir
            os.execv("/proc/self/exe", [sys.executable] + sys.argv)
        os.waitpid(child_pid, 0)
        sys.exit(0)

    try:
        setup_cgroups(pid)
        setup_network(pid)
        os.waitpid(pid, 0)
    finally:
        print("\n[CLEANUP] Tearing down container environment...")
        subprocess.run(["ip", "link", "delete", f"veth{pid}"], stderr=subprocess.DEVNULL)
        subprocess.run(["umount", "-l", os.path.join(run_dir, "merged")], stderr=subprocess.DEVNULL)
        shutil.rmtree(run_dir, ignore_errors=True)
        teardown_cgroups()
