import ipaddress
import os

CIDR_FILE = "cidr.txt"
PART_DIR = "parts"
CHUNK_SIZE = 10000

os.makedirs(PART_DIR, exist_ok=True)

part_id = 1
count = 0
out = None


def open_part():
    global part_id, count, out

    if out:
        out.close()

    filename = f"{PART_DIR}/part_{part_id:05d}.txt"
    print(f"Creating {filename}")

    out = open(filename, "w", encoding="utf-8")
    count = 0
    part_id += 1


open_part()

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

            out.write(f"{ip}\n")
            count += 1

            if count >= CHUNK_SIZE:
                open_part()

if out:
    out.close()

print("IP split completed.")
