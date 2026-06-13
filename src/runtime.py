import os
import sys
from namespaces import setup_namespaces
from rootfs import setup_rootfs
from cgroups import setup_cgroups
from mount import setup_mounts

def run_container(command):
	if os.getenv("CONTAINER_INIT") == "1":
		container_init(command)
		return

	pid = os.fork()
	if pid == 0:
		setup_namespaces()
		child_pid=os.fork()
		if child_pid==0:
			os.environ["CONTAINER_INIT"] = "1"
			os.execv("/proc/self/exe", [sys.executable] + sys.argv)
		else:
			os.waitpid(child_pid, 0)
			sys.exit(0)
	else:
		setup_cgroups(pid)
		os.waitpid(pid, 0)

def container_init(command):
	setup_rootfs()
	setup_mounts()

	os.execvp(command[0], command)
