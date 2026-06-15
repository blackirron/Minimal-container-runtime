#!/usr/bin/env python3
import subprocess, os, sys

def run(cmd): subprocess.run(cmd, shell=True)

if os.geteuid() != 0:
    print("Run with sudo."); sys.exit(1)

run("ip link show appnet &>/dev/null || (ip link add name appnet type bridge && ip link set appnet up && ip addr add 10.0.0.1/24 dev appnet)")
run("sysctl -w net.ipv4.ip_forward=1")
run("echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-mdocker.conf")  # survives reboot
run("iptables -t nat -C POSTROUTING -s 10.0.0.0/24 -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE")
run("iptables -C FORWARD -i appnet -j ACCEPT 2>/dev/null || iptables -A FORWARD -i appnet -j ACCEPT")
run("iptables -C FORWARD -o appnet -j ACCEPT 2>/dev/null || iptables -A FORWARD -o appnet -j ACCEPT")

print("Host ready.")
