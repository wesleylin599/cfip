#!/usr/bin/env python3

import concurrent.futures
import ipaddress
import re
import subprocess
import sys
from pathlib import Path


DOMAIN = "api.090227.xyz"
PORT = 443

CONNECT_TIMEOUT = 5
MAX_TIME = 8

# 每个 runner 同时探测多少 IP
WORKERS = 30


# Cloudflare colo -> country
#
# 这里不使用 GeoIP。
# 国家完全由 Cloudflare 返回的 colo 决定。
#
COLO_COUNTRY = {
    # Asia
    "ICN": "KR",
    "NRT": "JP",
    "KIX": "JP",
    "HND": "JP",
    "HKG": "HK",
    "TPE": "TW",
    "SIN": "SG",
    "BKK": "TH",
    "KUL": "MY",
    "MNL": "PH",
    "CGK": "ID",
    "DEL": "IN",
    "BOM": "IN",
    "MAA": "IN",
    "BLR": "IN",

    # China / Greater China
    "PEK": "CN",
    "PVG": "CN",
    "CAN": "CN",
    "CTU": "CN",
    "WUH": "CN",

    # Oceania
    "SYD": "AU",
    "MEL": "AU",
    "BNE": "AU",
    "PER": "AU",
    "AKL": "NZ",

    # Europe
    "AMS": "NL",
    "LHR": "GB",
    "MAN": "GB",
    "FRA": "DE",
    "MUC": "DE",
    "BER": "DE",
    "CDG": "FR",
    "ORY": "FR",
    "MAD": "ES",
    "BCN": "ES",
    "LIS": "PT",
    "DUB": "IE",
    "ZRH": "CH",
    "VIE": "AT",
    "BRU": "BE",
    "CPH": "DK",
    "ARN": "SE",
    "OSL": "NO",
    "HEL": "FI",
    "WAW": "PL",
    "PRG": "CZ",
    "BUD": "HU",
    "OTP": "RO",
    "IST": "TR",
    "ATH": "GR",
    "MXP": "IT",
    "FCO": "IT",
    "MIL": "IT",

    # North America
    "LAX": "US",
    "SJC": "US",
    "SFO": "US",
    "SEA": "US",
    "PDX": "US",
    "LAS": "US",
    "PHX": "US",
    "DEN": "US",
    "DFW": "US",
    "IAH": "US",
    "ORD": "US",
    "ATL": "US",
    "MIA": "US",
    "IAD": "US",
    "DCA": "US",
    "JFK": "US",
    "EWR": "US",
    "BOS": "US",
    "MSP": "US",
    "DTW": "US",
    "YYZ": "CA",
    "YUL": "CA",
    "YVR": "CA",

    # South America
    "GRU": "BR",
    "GIG": "BR",
    "EZE": "AR",
    "SCL": "CL",
    "LIM": "PE",
    "BOG": "CO",

    # Middle East
    "DXB": "AE",
    "AUH": "AE",
    "DOH": "QA",
    "RUH": "SA",
    "JED": "SA",
    "TLV": "IL",
    "AMM": "JO",

    # Africa
    "JNB": "ZA",
    "CPT": "ZA",
    "NBO": "KE",
    "CAI": "EG",
}


COLO_RE = re.compile(
    r"^colo=([A-Z0-9]{3})$",
    re.MULTILINE
)


def probe(ip):
    """
    Probe one Cloudflare IP using --resolve.

    Returns:
        (ip, colo, country)
    """

    cmd = [
        "curl",
        "-sS",
        "--noproxy", "*",
        "--connect-timeout", str(CONNECT_TIMEOUT),
        "--max-time", str(MAX_TIME),
        "--resolve", f"{DOMAIN}:{PORT}:{ip}",
        f"https://{DOMAIN}/cdn-cgi/trace",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=MAX_TIME + 3,
        )

        output = result.stdout

        match = COLO_RE.search(output)

        if not match:
            return ip, None, None

        colo = match.group(1)
        country = COLO_COUNTRY.get(colo)

        return ip, colo, country

    except subprocess.TimeoutExpired:
        return ip, None, None

    except Exception:
        return ip, None, None


def valid_ip(value):
    try:
        ip = ipaddress.ip_address(value)
        return ip.version == 4
    except ValueError:
        return False


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python3 02_cfprobe.py "
            "<input.txt> <output.txt>"
        )
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        raise FileNotFoundError(input_file)

    ips = []

    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            ip = line.strip()

            if not ip:
                continue

            if valid_ip(ip):
                ips.append(ip)

    total = len(ips)

    print(f"[INFO] Input IPs: {total}")
    print(f"[INFO] Workers: {WORKERS}")
    print(f"[INFO] Target: https://{DOMAIN}/cdn-cgi/trace")
    print()

    success = 0
    unknown = 0
    failed = 0

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_file.open(
        "w",
        encoding="utf-8",
        buffering=1,
    ) as out:

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=WORKERS
        ) as executor:

            futures = {
                executor.submit(probe, ip): ip
                for ip in ips
            }

            for index, future in enumerate(
                concurrent.futures.as_completed(futures),
                1
            ):
                ip, colo, country = future.result()

                if colo is None:
                    failed += 1

                    print(
                        f"[{index}/{total}] "
                        f"{ip} -> FAILED"
                    )

                    continue

                if country is None:
                    unknown += 1

                    print(
                        f"[{index}/{total}] "
                        f"{ip} -> {colo} -> UNKNOWN"
                    )

                    continue

                success += 1

                line = f"{ip}:{PORT}#{country}\n"
                out.write(line)

                print(
                    f"[{index}/{total}] "
                    f"{ip} -> {colo} -> {country}"
                )

    print()
    print("========================================")
    print(f"Total   : {total}")
    print(f"Success : {success}")
    print(f"Unknown : {unknown}")
    print(f"Failed  : {failed}")
    print(f"Output  : {output_file}")
    print("========================================")


if __name__ == "__main__":
    main()
