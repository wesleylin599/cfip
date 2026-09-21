#!/usr/bin/env python3

from pathlib import Path


RESULTS_DIR = Path("results")
OUTPUT_FILE = Path("cidrip.txt")


def ip_sort_key(line):
    ip = line.split(":", 1)[0]

    try:
        return tuple(int(x) for x in ip.split("."))
    except Exception:
        return (999, 999, 999, 999)


def main():
    if not RESULTS_DIR.exists():
        raise RuntimeError("results directory not found")

    lines = set()

    for file in sorted(RESULTS_DIR.glob("part_*.txt")):
        print(f"[READ] {file}")

        with file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                if "#" not in line:
                    continue

                lines.add(line)

    sorted_lines = sorted(
        lines,
        key=ip_sort_key
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        for line in sorted_lines:
            f.write(line + "\n")

    print()
    print("========================================")
    print(f"Output : {OUTPUT_FILE}")
    print(f"Lines  : {len(sorted_lines)}")
    print("========================================")


if __name__ == "__main__":
    main()
