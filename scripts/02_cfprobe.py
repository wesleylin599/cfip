#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

import airportsdata


DOMAIN = "api.090227.xyz"
PORT = 443

# 单个 Worker 内部并发
WORKERS = 30

# curl 超时
CONNECT_TIMEOUT = 5
MAX_TIME = 8


# 加载 IATA 数据
AIRPORTS = airportsdata.load("IATA")


# Cloudflare Colo 的少量特殊/常见代码补充
SPECIAL_COUNTRIES = {
    "AMS": "NL",
    "NRT": "JP",
    "HND": "JP",
    "KIX": "JP",
    "ICN": "KR",
    "GMP": "KR",
    "HKG": "HK",
    "SIN": "SG",
    "TPE": "TW",
    "FRA": "DE",
    "MUC": "DE",
    "LHR": "GB",
    "MAN": "GB",
    "CDG": "FR",
    "MAD": "ES",
    "BCN": "ES",
    "FCO": "IT",
    "ZRH": "CH",
    "VIE": "AT",
    "WAW": "PL",
    "PRG": "CZ",
    "CPH": "DK",
    "ARN": "SE",
    "HEL": "FI",
    "OSL": "NO",
    "BRU": "BE",
    "LIS": "PT",
    "DUB": "IE",

    "SYD": "AU",
    "MEL": "AU",
    "BNE": "AU",
    "PER": "AU",

    "LAX": "US",
    "SJC": "US",
    "SFO": "US",
    "SEA": "US",
    "PDX": "US",
    "DEN": "US",
    "ORD": "US",
    "DFW": "US",
    "ATL": "US",
    "MIA": "US",
    "IAD": "US",
    "EWR": "US",
    "JFK": "US",
    "BOS": "US",
    "PHL": "US",
    "MSP": "US",
    "DTW": "US",
    "CLT": "US",
    "PHX": "US",
    "LAS": "US",

    "YYZ": "CA",
    "YVR": "CA",
    "YUL": "CA",
    "YYC": "CA",

    "GRU": "BR",
    "EZE": "AR",
    "SCL": "CL",
    "LIM": "PE",
    "BOG": "CO",

    "JNB": "ZA",
    "CPT": "ZA",

    "DXB": "AE",
    "AUH": "AE",
    "DOH": "QA",
    "RUH": "SA",
    "TLV": "IL",

    "DEL": "IN",
    "BOM": "IN",
    "MAA": "IN",
    "BLR": "IN",
    "HYD": "IN",

    "BKK": "TH",
    "KUL": "MY",
    "CGK": "ID",
    "MNL": "PH",
    "SGN": "VN",
    "HAN": "VN",
}


def colo_to_country(colo):
    colo = colo.upper()

    if colo in SPECIAL_COUNTRIES:
        return SPECIAL_COUNTRIES[colo]

    airport = AIRPORTS.get(colo)

    if airport:
        country = airport.get("country")

        if country:
            return country.upper()

    return "XX"


def probe(ip):
    """
    强制把 api.090227.xyz:443
    连接到指定 IP。
    """

    command = [
        "curl",
        "-sS",
        "--noproxy",
        "*",

        "--connect-timeout",
        str(CONNECT_TIMEOUT),

        "--max-time",
        str(MAX_TIME),

        "--resolve",
        f"{DOMAIN}:{PORT}:{ip}",

        "-D",
        "-",

        "-o",
        "/dev/null",

        f"https://{DOMAIN}/check",
    ]

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=MAX_TIME + 3
        )

        headers = result.stdout

        # HTTP 状态
        status_match = re.search(
            r"HTTP/\d(?:\.\d)?\s+(\d+)",
            headers,
            re.IGNORECASE
        )

        status = (
            status_match.group(1)
            if status_match
            else "000"
        )

        # CF-Ray
        ray_match = re.search(
            r"^CF-RAY:\s*([^\r\n]+)",
            headers,
            re.IGNORECASE |
            re.MULTILINE
        )

        if not ray_match:
            return {
                "ip": ip,
                "status": status,
                "colo": "",
                "country": "XX",
                "success": False,
            }

        ray = ray_match.group(1).strip()

        # CF-Ray:
        #
        # a3e70984b87af5da-AMS
        #
        colo_match = re.search(
            r"-([A-Z0-9]{3})$",
            ray
        )

        if not colo_match:
            return {
                "ip": ip,
                "status": status,
                "colo": "",
                "country": "XX",
                "success": False,
            }

        colo = colo_match.group(1)

        country = colo_to_country(
            colo
        )

        return {
            "ip": ip,
            "status": status,
            "colo": colo,
            "country": country,
            "success": True,
        }

    except Exception:

        return {
            "ip": ip,
            "status": "000",
            "colo": "",
            "country": "XX",
            "success": False,
        }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True
    )

    parser.add_argument(
        "--output",
        required=True
    )

    args = parser.parse_args()

    os.makedirs(
        os.path.dirname(args.output) or ".",
        exist_ok=True
    )

    with open(
        args.input,
        "r",
        encoding="utf-8"
    ) as f:

        ips = [
            x.strip()
            for x in f
            if x.strip()
        ]

    total = len(ips)

    print(
        f"Testing {total} IPs..."
    )

    results = []

    completed = 0

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(
                probe,
                ip
            ): ip
            for ip in ips
        }

        for future in as_completed(
            futures
        ):

            result = future.result()

            completed += 1

            if result["success"]:

                ip = result["ip"]
                country = result["country"]

                # 最终格式
                results.append(
                    f"{ip}:443#{country}"
                )

                print(
                    f"[{completed}/{total}] "
                    f"{ip} -> "
                    f"{result['colo']} "
                    f"{country} "
                    f"HTTP {result['status']}"
                )

            else:

                print(
                    f"[{completed}/{total}] "
                    f"{result['ip']} -> FAILED"
                )

    # 排序
    results.sort()

    with open(
        args.output,
        "w",
        encoding="utf-8"
    ) as f:

        for line in results:
            f.write(line + "\n")

    print()
    print(
        f"Success: {len(results)}/{total}"
    )

    print(
        f"Output: {args.output}"
    )


if __name__ == "__main__":
    main()
