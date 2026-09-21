#!/usr/bin/env python3

import ipaddress
import os

CIDR_FILE = "cidr.txt"
PART_DIR = "parts"

# 每个 GitHub Actions Job 处理多少 IP
CHUNK_SIZE = 5000


def main():
    os.makedirs(PART_DIR, exist_ok=True)

    part_id = 1
    count = 0
    total = 0

    output = None

    def open_part():
        nonlocal part_id, count, output

        if output:
            output.close()

        filename = os.path.join(
            PART_DIR,
            f"part_{part_id:05d}.txt"
        )

        print(f"Create: {filename}")

        output = open(
            filename,
            "w",
            encoding="utf-8"
        )

        count = 0
        part_id += 1

    open_part()

    with open(
        CIDR_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            try:
                network = ipaddress.ip_network(
                    line,
                    strict=False
                )
            except ValueError:
                print(
                    f"Invalid CIDR: {line}"
                )
                continue

            if network.version != 4:
                print(
                    f"Skip IPv6: {network}"
                )
                continue

            print(
                f"Processing: {network}"
            )

            for ip in network.hosts():

                output.write(
                    str(ip) + "\n"
                )

                count += 1
                total += 1

                if count >= CHUNK_SIZE:
                    open_part()

    if output:
        output.close()

    # 删除最后可能产生的空文件
    for filename in os.listdir(PART_DIR):

        path = os.path.join(
            PART_DIR,
            filename
        )

        if os.path.isfile(path) and os.path.getsize(path) == 0:
            os.remove(path)

    parts = len(
        os.listdir(PART_DIR)
    )

    print()
    print("====================")
    print(f"Total IP : {total}")
    print(f"Parts    : {parts}")
    print("====================")


if __name__ == "__main__":
    main()
