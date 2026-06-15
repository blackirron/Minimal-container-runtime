# minimal-container-runtime

A minimal Linux container runtime built from scratch in Python. No Docker, no containerd — just raw Linux syscalls: namespaces, cgroups, OverlayFS, pivot_root, and veth networking. Ships with an Adminer PHP database UI running inside the container.

---

## Architecture

```
cli.py
  └── runtime.py          # orchestrates host + container phases
        ├── namespaces.py # unshare(2): PID, mount, net, UTS
        ├── rootfs.py     # overlayfs + pivot_root + DNS injection
        ├── cgroups.py    # cgroup v2: memory, CPU, PID limits
        └── network.py    # veth pair + bridge + NAT routing
```

### How a container boots

```
Host process
  │
  ├── preflight_check()          verify appnet bridge exists
  ├── fork()  ─────────────────► Namespace process
  │                                  unshare(NEWPID|NEWNS|NEWNET|NEWUTS)
  │                                  fork()  ──────────────────► Container init
  │                                                                  setup_container_fs()
  │                                                                    mount overlayfs
  │                                                                    inject /etc/resolv.conf
  │                                                                    bind /var/www
  │                                                                    mount /proc
  │                                                                    pivot_root()
  │                                                                    execvp(command)
  ├── setup_cgroups(pid)         memory/CPU/PID limits
  ├── setup_network(pid)         veth → appnet bridge → NAT
  └── waitpid() → finally:       cleanup veth, umount, rmtree, cgroup
```

---

## Features

| Feature | Implementation |
|---|---|
| Process isolation | `CLONE_NEWPID` via `unshare(2)` |
| Filesystem isolation | OverlayFS + `pivot_root(2)` |
| Network isolation | `CLONE_NEWNET` + veth pair |
| Resource limits | cgroup v2 (memory, CPU, PIDs) |
| Internet access | NAT via `iptables MASQUERADE` |
| DNS | Static `resolv.conf` injected post-overlay-mount |
| Persistent workspace | bind-mount `./workspace` → `/var/www` |
| Copy-on-write rootfs | OverlayFS upper/lower/work/merged |
| Database UI | Adminer v5.4.1 on `http://10.0.0.2:8080` |

---

## Requirements

- Linux kernel 5.x+ with cgroup v2 enabled
- Python 3.10+
- `iproute2`, `iptables`, `nsenter`
- Alpine-based rootfs at `./rootfs/`
- Adminer pre-downloaded at `./workspace/adminer-core.php`

---

## Setup

### 1. Host prerequisites (once)

```bash
sudo python3 src/setup_host.py
```

This creates the `appnet` bridge, enables IP forwarding (persisted to `/etc/sysctl.d/99-mdocker.conf`), and sets up iptables NAT rules. Idempotent — safe to run multiple times.

### 2. Pre-seed Adminer (once)

```bash
wget https://github.com/vrana/adminer/releases/download/v5.4.1/adminer-5.4.1.php \
     -O workspace/adminer-core.php
```

> Alpine busybox wget has TLS limitations that cause broken pipe errors on some GitHub redirects. Download on the host instead.

### 3. Run

```bash
sudo python3 src/cli.py run /entrypoint.sh
```

Open `http://10.0.0.2:8080` in your browser.

---

## Usage

```bash
# Run the full stack (PHP + Adminer)
sudo python3 src/cli.py run /entrypoint.sh

# Drop into a shell inside the container
sudo python3 src/cli.py run /bin/bash

# Run any command
sudo python3 src/cli.py run /bin/sh -c "echo hello from container"
```

---

## Adminer Login

| Field | Value |
|---|---|
| System | SQLite 3 |
| Username | *(leave empty)* |
| Password | *(leave empty)* |
| Database | `/var/www/dev.db` |

The `login()` bypass in `workspace/index.php` accepts any credentials.

---

## Resource Limits (cgroup v2)

| Resource | Limit |
|---|---|
| Memory | 256 MB |
| CPU | 50% (50ms per 100ms window) |
| Max PIDs | 64 |

Cgroup at `/sys/fs/cgroup/mycontainer`, cleaned up on container exit.

---

## Networking

```
Container (10.0.0.2)
    eth0 ──── veth{pid} ──── appnet bridge (10.0.0.1) ──── host NIC ──── internet
                                    │
                              iptables NAT
                           MASQUERADE 10.0.0.0/24
```

The veth pair is named `veth{pid}` / `vethc{pid}` and deleted on cleanup.

---

## Known Issues

| Issue | Status | Notes |
|---|---|---|
| `appnet` bridge lost on reboot | Known | Re-run `setup_host.py` after reboot. iptables rules also reset unless you use `iptables-persistent`. |
| Alpine busybox wget TLS failures | Known | Pre-seed `adminer-core.php` from host. In-container HTTPS to GitHub is unreliable. |
| `[INIT] Terminating...` spam on Ctrl+C | Known | `kill 0` in the trap catches itself recursively. Cosmetic only — container exits correctly. |
| `NO-CARRIER` on appnet in logs | Not a bug | Bridges show NO-CARRIER when no physical cable is attached. Normal behavior. |

---

## Project Structure

```
minimal-container-runtime/
├── src/
│   ├── cli.py            # argparse entrypoint
│   ├── runtime.py        # container lifecycle orchestration
│   ├── namespaces.py     # linux namespace isolation
│   ├── rootfs.py         # overlayfs, pivot_root, DNS, bind mounts
│   ├── cgroups.py        # cgroup v2 resource limits
│   ├── network.py        # veth + bridge + routing
│   └── setup_host.py     # one-time host prerequisites
├── rootfs/               # alpine base image (not committed)
│   └── entrypoint.sh     # container init script
├── workspace/            # bind-mounted into /var/www
│   ├── adminer-core.php  # adminer v5.4.1
│   ├── index.php         # bypass wrapper
│   └── dev.db            # sqlite database
├── notes/                # design notes per subsystem
└── scripts/              # helper shell scripts
```

---

## Future Scope

- **User namespace mapping** (`CLONE_NEWUSER`) — run container as non-root on host, map uid 0 inside to unprivileged uid outside
- **Image layering** — pull and cache OCI-compatible image layers, stack multiple lowerdir layers in OverlayFS
- **Port forwarding** — `iptables DNAT` rules to expose container ports to host or LAN
- **Multiple containers** — assign IPs dynamically from a pool (`10.0.0.2`, `.3`, `.4`...), support concurrent runs
- **`ps`-style container listing** — track running container PIDs in a state file, add `mdocker ps` subcommand
- **Seccomp filtering** — block dangerous syscalls (`ptrace`, `mount`, `reboot`) via `prctl(PR_SET_SECCOMP)`
- **Capabilities dropping** — use `prctl(PR_SET_CAPS)` to drop all capabilities after setup
- **iptables-persistent** — auto-save NAT rules so they survive reboot without re-running setup
- **Resource limit CLI flags** — `--memory 128m --cpus 0.25 --pids 32` passed through to cgroups
