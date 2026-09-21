import glob
import ipaddress
import os


RESULT_DIR = "results"
OUTPUT_FILE = "cidrip.txt"


lines = set()


files = glob.glob(
    os.path.join(
        RESULT_DIR,
        "part_*.txt"
    )
)


print(
    f"Found {len(files)} result files"
)


for filename in files:

    print(
        f"Reading {filename}"
    )

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if line:
                lines.add(line)


def sort_key(line):

    ip = line.split(":", 1)[0]

    return ipaddress.ip_address(ip)


sorted_lines = sorted(
    lines,
    key=sort_key
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    for line in sorted_lines:

        f.write(
            line + "\n"
        )


print()
print(
    f"Total: {len(sorted_lines)}"
)

print(
    f"Output: {OUTPUT_FILE}"
)
