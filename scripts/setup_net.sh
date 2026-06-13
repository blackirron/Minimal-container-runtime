#!/bin/bash
set -e
echo "[INFO] Creating appnet bridge..."
# 1. Create the virtual bridge
sudo ip link add name appnet type bridge 2>/dev/null || true
# 2. Assign the bridge an IP address (This acts as the container's gateway)
sudo ip addr add 10.0.0.1/24 dev appnet 2>/dev/null || true
sudo ip link set appnet up

echo "[INFO] Enabling IP Forwarding and NAT..."
# 3. Tell the Linux kernel it is allowed to forward network packets
sudo sysctl -w net.ipv4.ip_forward=1
# 4. Set up an iptables rule to translate container traffic to your host's Wi-Fi
sudo iptables -t nat -C POSTROUTING -s 10.0.0.0/24 -j MASQUERADE 2>/dev/null \
    || sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE

echo "[INFO] Allowing forwarded traffic for appnet (Docker sets FORWARD policy to DROP)..."
# 5. Explicitly permit forwarding to/from appnet.
#    Docker installs DOCKER-USER/DOCKER-FORWARD jump chains in FORWARD and
#    sets the chain policy to DROP. Those chains have no rule for appnet,
#    so traffic falls through to the policy and gets silently dropped.
#    These ACCEPT rules, appended after Docker's chains, catch it before
#    the DROP policy is reached.
sudo iptables -C FORWARD -i appnet -j ACCEPT 2>/dev/null \
    || sudo iptables -A FORWARD -i appnet -j ACCEPT
sudo iptables -C FORWARD -o appnet -j ACCEPT 2>/dev/null \
    || sudo iptables -A FORWARD -o appnet -j ACCEPT

echo "[SUCCESS] Host network 'appnet' is ready on 10.0.0.1"
