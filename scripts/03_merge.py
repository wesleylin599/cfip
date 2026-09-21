#!/usr/bin/env python3

import glob
import ipaddress
import os


RESULT_DIR = "results"
OUTPUT = "cidrip.txt"


def ip_sort(line):

    ip = line.split(":", 1)[0]

    return ipaddress.ip_address(ip)


def main():

    files = sorted(
        glob.glob(
            os.path.join(
                RESULT_DIR,
                "part_*.txt"
            )
        )
    )

    print(
        f"Found {len(files)} result files"
    )

    data = set()

    for filename in files:

        print(
            f"Reading {filename}"
        )

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as f:

                for line in f:

                    line = line.strip()

                    if line:
                        data.add(line)

        except Exception as e:

            print(
                f"Failed: {filename}: {e}"
            )

    result = sorted(
        data,
        key=ip_sort
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        for line in result:

            f.write(
                line + "\n"
            )

    print()
    print(
        f"Total: {len(result)}"
    )

    print(
        f"Output: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
