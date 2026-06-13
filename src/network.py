import subprocess 

def setup_network(container_pid):		#notes in ../notes directory
    veth_host = f"veth{container_pid}"
    veth_guest = f"vethc{container_pid}"

    subprocess.run(["ip", "link", "add", veth_host, "type", "veth", "peer", "name", veth_guest], check=True)

    subprocess.run(["ip", "link", "set", veth_host, "master", "appnet"], check=True)
    subprocess.run(["ip", "link", "set", veth_host, "up"], check=True)

    subprocess.run(["ip", "link", "set", veth_guest, "netns", str(container_pid)], check=True)

    nsenter = ["nsenter", "-t", str(container_pid), "-n", "ip"]

    subprocess.run(nsenter + ["link", "set", "lo", "up"], check=True)

    subprocess.run(nsenter + ["link", "set", veth_guest, "name", "eth0"], check=True)

    subprocess.run(nsenter + ["addr", "add", "10.0.0.2/24", "dev", "eth0"], check=True)
    subprocess.run(nsenter + ["link", "set", "eth0", "up"], check=True)

    subprocess.run(nsenter + ["route", "add", "default", "via", "10.0.0.1"], check=True)
