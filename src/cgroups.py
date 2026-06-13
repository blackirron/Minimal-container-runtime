import os

CGROUP_BASE = "/sys/fs/cgroup/mycontainer"

def setup_cgroups(host_pid):
	os.makedirs(CGROUP_BASE, exist_ok=True)

	with open(f"{CGROUP_BASE}/memory.max", "w") as f:
		f.write("256M")

	with open(f"{CGROUP_BASE}/pids.max", "w") as f:
		f.write("64")

	with open(f"{CGROUP_BASE}/cpu.max", "w") as f:
		f.write("50000 100000")

	with open(f"{CGROUP_BASE}/cgroup.procs", "w") as f:
		f.write(str(host_pid))
