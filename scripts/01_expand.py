import ipaddress
import os

CIDR_FILE = "cidr.txt"
PART_DIR = "parts"

# 每个分片多少 IP
CHUNK_SIZE = 10000

os.makedirs(PART_DIR, exist_ok=True)

ips = []

with open(CIDR_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        try:
            network = ipaddress.ip_network(line, strict=False)
        except ValueError:
            print(f"Invalid CIDR: {line}")
            continue

        if network.version != 4:
            continue

        for ip in network.hosts():
            ips.append(str(ip))

            if len(ips) >= CHUNK_SIZE:
                break

        # 这里不能简单 break CIDR，需要完整处理
