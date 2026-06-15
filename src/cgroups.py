import os
import shutil

CGROUP_BASE = "/sys/fs/cgroup/mycontainer"

def setup_cgroups(host_pid):
    os.makedirs(CGROUP_BASE, exist_ok=True)
    with open(f"{CGROUP_BASE}/memory.max", "w") as f:
        f.write("268435456")          # 256MB in bytes — cgroup v2 requires raw bytes
    with open(f"{CGROUP_BASE}/pids.max", "w") as f:
        f.write("64")
    with open(f"{CGROUP_BASE}/cpu.max", "w") as f:
        f.write("50000 100000")       # 50ms per 100ms window = 50% CPU
    with open(f"{CGROUP_BASE}/cgroup.procs", "w") as f:
        f.write(str(host_pid))

def teardown_cgroups():
    try:
        shutil.rmtree(CGROUP_BASE)
    except Exception:
        pass
