# 🚢 Minimal Container Runtime

> **No Docker. No containerd. Just pure Python and raw Linux syscalls.** Welcome to a bare-bones, educational Linux container runtime built entirely from scratch. This project strips away the abstraction of modern container engines to expose the underlying Linux primitives: **namespaces, cgroups, OverlayFS, `pivot_root`, and veth networking**.

To demonstrate its capabilities, the runtime ships with a fully functional **Adminer PHP database UI** running securely isolated inside the container.

---

##  System Architecture

The runtime relies on a clean, modular architecture separating the host orchestration from the isolated container lifecycle.

### Code Organization

```text
cli.py (Entrypoint)
  └── runtime.py          # Orchestrates host + container phases
        ├── namespaces.py # unshare(2): PID, mount, net, UTS
        ├── rootfs.py     # overlayfs + pivot_root + DNS injection
        ├── cgroups.py    # cgroup v2: memory, CPU, PID limits
        └── network.py    # veth pair + bridge + NAT routing

```

### The Boot Sequence

Understanding how the container spins up is key to understanding Linux isolation. Here is the step-by-step process lifecycle:

```text
Host process
  │
  ├── 1. preflight_check()       → Verifies appnet bridge exists
  ├── 2. fork()  ──────────────► [Namespace Process]
  │                                │ unshare(NEWPID|NEWNS|NEWNET|NEWUTS)
  │                                └── fork()  ──────────► [Container Init]
  │                                                          │ setup_container_fs()
  │                                                          │  ├─ mount overlayfs
  │                                                          │  ├─ inject /etc/resolv.conf
  │                                                          │  ├─ bind /var/www
  │                                                          │  ├─ mount /proc
  │                                                          │  └─ pivot_root()
  │                                                          └── execvp(command)
  ├── 3. setup_cgroups(pid)      → Enforces memory/CPU/PID limits
  ├── 4. setup_network(pid)      → Attaches veth → appnet bridge → NAT
  └── 5. waitpid()               → Listens for exit
         └── finally:            → Cleans up veth, umount, rmtree, cgroup

```

---

##  Core Features

| Capability | Under the Hood Implementation |
| --- | --- |
| **Process Isolation** | `CLONE_NEWPID` via `unshare(2)` |
| **Filesystem Isolation** | OverlayFS + `pivot_root(2)` |
| **Network Isolation** | `CLONE_NEWNET` + Virtual Ethernet (veth) pairs |
| **Resource Limits** | cgroup v2 (Constrains memory, CPU, and PIDs) |
| **Internet Access** | NAT routing via `iptables MASQUERADE` |
| **DNS Resolution** | Static `resolv.conf` injected post-overlay-mount |
| **Persistent Workspace** | Bind-mounting `./workspace` directly into `/var/www` |
| **Copy-on-Write Root** | OverlayFS architecture (upper/lower/work/merged) |
| **Out-of-the-box UI** | Adminer v5.4.1 running live on `http://10.0.0.2:8080` |

---

##  Prerequisites

Before you spin up the runtime, ensure your environment meets the following requirements:

* **Kernel:** Linux kernel 5.x+ (with cgroup v2 enabled)
* **Language:** Python 3.10+
* **System Tools:** `iproute2`, `iptables`, `nsenter`
* **Filesystem:** An Alpine-based rootfs located at `./rootfs/`
* **Workspace:** Adminer pre-downloaded at `./workspace/adminer-core.php`

---

##  Quick Start Guide

### Step 1: Host Prerequisites (One-time setup)

First, configure the host machine's networking. This step creates the `appnet` bridge, enables IP forwarding (persisted to `/etc/sysctl.d/99-mdocker.conf`), and establishes iptables NAT rules.

```bash
sudo python3 src/setup_host.py

```

> ** Tip:** This script is idempotent. It is completely safe to run it multiple times.

### Step 2: Pre-seed Adminer (One-time setup)

Download the Adminer core file to your workspace.

```bash
wget https://github.com/vrana/adminer/releases/download/v5.4.1/adminer-5.4.1.php \
     -O workspace/adminer-core.php

```

> ** Note on Alpine wget:** Alpine's busybox `wget` has TLS limitations causing broken pipe errors on some GitHub redirects. It is highly recommended to download this on your host machine before running the container.

### Step 3: Run the Container

Launch the entry point script to boot the container and start the PHP server.

```bash
sudo python3 src/cli.py run /entrypoint.sh

```

Once running, open your browser and navigate to **`http://10.0.0.2:8080`**.

---

##  Usage & Commands

You aren't limited to just running the pre-packaged web server. You can use the CLI to drop into different environments:

```bash
# 1. Run the full stack (PHP + Adminer)
sudo python3 src/cli.py run /entrypoint.sh

# 2. Drop directly into an isolated interactive shell
sudo python3 src/cli.py run /bin/bash

# 3. Execute a single isolated command and exit
sudo python3 src/cli.py run /bin/sh -c "echo hello from the container!"

```

---

##  Environment Specifications

### Adminer Database Login

The runtime includes a bypassed `login()` wrapper in `workspace/index.php`, meaning it will accept any credentials for testing purposes.

| Field | Value |
| --- | --- |
| **System** | SQLite 3 |
| **Username** | *(Leave completely empty)* |
| **Password** | *(Leave completely empty)* |
| **Database** | `/var/www/dev.db` |

### Resource Limits (cgroup v2)

The container is strictly sandboxed. These limits are tracked at `/sys/fs/cgroup/mycontainer` and are automatically cleaned up when the container exits.

* **Memory:** Max 256 MB
* **CPU:** Max 50% utilization (50ms quota per 100ms window)
* **Processes:** Maximum 64 PIDs

### Network Topology

```text
Container (10.0.0.2)
    eth0 ──── veth{pid} ──── appnet bridge (10.0.0.1) ──── Host NIC ──── Internet
                                    │
                              iptables NAT
                         (MASQUERADE 10.0.0.0/24)

```

*The veth pair is named dynamically as `veth{pid}` / `vethc{pid}` and is destroyed gracefully upon teardown.*

---

##  Project Directory

```text
minimal-container-runtime/
├── src/
│   ├── cli.py            # Argparse entrypoint
│   ├── runtime.py        # Container lifecycle orchestration
│   ├── namespaces.py     # Linux namespace isolation handling
│   ├── rootfs.py         # OverlayFS, pivot_root, DNS, bind mounts
│   ├── cgroups.py        # cgroup v2 resource limits
│   ├── network.py        # veth + bridge + routing logic
│   └── setup_host.py     # One-time host networking prerequisites
├── rootfs/               # Alpine base image directory (not committed)
│   └── entrypoint.sh     # Container init startup script
├── workspace/            # Bind-mounted directly into /var/www
│   ├── adminer-core.php  # Adminer v5.4.1 binary
│   ├── index.php         # Custom login bypass wrapper
│   └── dev.db            # Local SQLite database
├── notes/                # Architecture & design notes per subsystem
└── scripts/              # Helper shell utilities

```

---

##  Known Issues & Quirks

| Status | Issue | Details |
| --- | --- | --- |
|  | **`appnet` bridge lost on reboot** | Re-run `setup_host.py` after a system reboot. `iptables` rules will also reset unless you install and configure `iptables-persistent`. |
|  | **Alpine busybox TLS failures** | Pre-seed `adminer-core.php` from the host. In-container HTTPS requests to GitHub are currently unreliable. |
|  | **`[INIT] Terminating...` spam** | Hitting `Ctrl+C` causes a recursive `kill 0` trap. This is cosmetic only; the container still exits and cleans up correctly. |
|  | **`NO-CARRIER` in host logs** | Bridges display `NO-CARRIER` when no physical cable is attached. This is normal Linux networking behavior. |

---

##  Future Roadmap

We are constantly looking to push this closer to a production-grade (yet minimal) runtime. Here is what's on the horizon:

### Security & Isolation

* **User Namespace Mapping (`CLONE_NEWUSER`):** Run the container as non-root on the host, mapping UID 0 inside to an unprivileged UID outside.
* **Seccomp Filtering:** Block dangerous syscalls (e.g., `ptrace`, `mount`, `reboot`) using `prctl(PR_SET_SECCOMP)`.
* **Capabilities Dropping:** Utilize `prctl(PR_SET_CAPS)` to strip all Linux capabilities after the initial setup phase.

### Networking & Data

* **Port Forwarding:** Implement `iptables DNAT` rules to easily expose container ports to the host machine or LAN.
* **iptables-persistent:** Auto-save NAT rules during `setup_host.py` so they survive host machine reboots.

### Orchestration & UX

* **Image Layering:** Support pulling and caching OCI-compatible image layers, stacking multiple `lowerdir` layers in OverlayFS.
* **Multiple Containers:** Dynamically assign IPs from a subnet pool (`10.0.0.2`, `.3`, `.4`) to support concurrent container execution.
* **Container Listing:** Track running PIDs in a state file to support a `mdocker ps` subcommand.
* **Dynamic Resource Flags:** Pass CLI arguments like `--memory 128m --cpus 0.25 --pids 32` directly through to the cgroups manager.
