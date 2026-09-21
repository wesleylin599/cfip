#!/usr/bin/env python3

import ipaddress
import json
import os
import shutil
from pathlib import Path

CIDR_FILE = Path("cidr.txt")
PARTS_DIR = Path("parts")

CHUNK_SIZE = 5000


def read_cidrs():
    if not CIDR_FILE.exists():
        raise FileNotFoundError("cidr.txt not found")

    networks = []

    with CIDR_FILE.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            try:
                network = ipaddress.ip_network(line, strict=False)
            except ValueError as e:
                print(f"[WARN] Invalid CIDR at line {line_no}: {line}")
                print(f"       {e}")
                continue

            if network.version != 4:
                print(f"[WARN] IPv6 skipped: {network}")
                continue

            networks.append(network)

    return networks


def main():
    networks = read_cidrs()

    if not networks:
        raise RuntimeError("No valid IPv4 CIDR found in cidr.txt")

    if PARTS_DIR.exists():
        shutil.rmtree(PARTS_DIR)

    PARTS_DIR.mkdir(parents=True, exist_ok=True)

    part_index = 1
    current = []

    total = 0

    def flush():
        nonlocal part_index, current

        if not current:
            return

        filename = PARTS_DIR / f"part_{part_index:05d}.txt"

        with filename.open("w", encoding="utf-8") as f:
            for ip in current:
                f.write(f"{ip}\n")

        print(f"[WRITE] {filename} -> {len(current)} IPs")

        part_index += 1
        current = []

    for network in networks:
        print(f"[CIDR] {network}")

        # 使用 hosts()：
        # IPv4 CIDR 的 network address / broadcast address 不参与探测。
        for ip in network.hosts():
            current.append(str(ip))
            total += 1

            if len(current) >= CHUNK_SIZE:
                flush()

    flush()

    parts = sorted(
        str(p)
        for p in PARTS_DIR.glob("part_*.txt")
    )

    if not parts:
        raise RuntimeError("No IP parts generated")

    matrix = {
        "include": [
            {
                "part": os.path.basename(p)
            }
            for p in parts
        ]
    }

    with open("matrix.json", "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False)

    print()
    print("========================================")
    print(f"Total IPs : {total}")
    print(f"Parts     : {len(parts)}")
    print("========================================")


if __name__ == "__main__":
    main()
