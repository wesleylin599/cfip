#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


DOMAIN = "api.090227.xyz"
PORT = 443

WORKERS = 30

CONNECT_TIMEOUT = 5
MAX_TIME = 8


# Cloudflare Colo → 国家
# 这里不要依赖 GeoIP
COLO_COUNTRY = {

    # Asia
    "ICN": "KR",
    "NRT": "JP",
    "KIX": "JP",
    "HKG": "HK",
    "TPE": "TW",
    "SIN": "SG",
    "KUL": "MY",
    "BKK": "TH",
    "CGK": "ID",
    "MNL": "PH",
    "SGN": "VN",
    "HAN": "VN",

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
    "CDG": "FR",
    "MRS": "FR",
    "MAD": "ES",
    "BCN": "ES",
    "FCO": "IT",
    "MXP": "IT",
    "ZRH": "CH",
    "VIE": "AT",
    "WAW": "PL",
    "PRG": "CZ",
    "CPH": "DK",
    "ARN": "SE",
    "HEL": "FI",
    "OSL": "NO",
    "DUB": "IE",
    "BRU": "BE",
    "LIS": "PT",
    "IST": "TR",
    "ATH": "GR",
    "BUC": "RO",
    "SOF": "BG",
    "RIX": "LV",
    "TLL": "EE",
    "VNO": "LT",

    # North America
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

    "MEX": "MX",

    # South America
    "GRU": "BR",
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

    # Africa
    "JNB": "ZA",
    "CPT": "ZA",
    "NBO": "KE",
    "LOS": "NG",
    "CAI": "EG",
}


def get_country(colo):

    return COLO_COUNTRY.get(
        colo.upper(),
        "XX"
    )


def probe(ip):

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

            timeout=MAX_TIME + 3,
        )

        headers = result.stdout

        # HTTP status
        status_match = re.search(
            r"HTTP/\d(?:\.\d)?\s+(\d+)",
            headers,
            re.IGNORECASE,
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
            re.IGNORECASE | re.MULTILINE,
        )

        if not ray_match:

            return None

        ray = ray_match.group(1).strip()

        # 例如：
        #
        # a3e70984b87af5da-AMS
        #
        colo_match = re.search(
            r"-([A-Z]{3})$",
            ray,
        )

        if not colo_match:

            return None

        colo = colo_match.group(1)

        country = get_country(colo)

        return (
            ip,
            colo,
            country,
            status,
        )

    except Exception:

        return None


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    os.makedirs(
        os.path.dirname(args.output)
        or ".",
        exist_ok=True,
    )

    with open(
        args.input,
        "r",
        encoding="utf-8",
    ) as f:

        ips = [
            x.strip()
            for x in f
            if x.strip()
        ]

    total = len(ips)

    print(
        f"Testing {total} IPs"
    )

    results = []

    completed = 0

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(
                probe,
                ip,
            ): ip
            for ip in ips
        }

        for future in as_completed(
            futures
        ):

            completed += 1

            ip = futures[future]

            result = future.result()

            if result:

                ip, colo, country, status = result

                print(
                    f"[{completed}/{total}] "
                    f"{ip} -> "
                    f"{colo} -> "
                    f"{country} "
                    f"HTTP={status}"
                )

                # 只输出已知国家
                if country != "XX":

                    results.append(
                        f"{ip}:443#{country}"
                    )

            else:

                print(
                    f"[{completed}/{total}] "
                    f"{ip} -> FAILED"
                )

    results = sorted(
        set(results)
    )

    with open(
        args.output,
        "w",
        encoding="utf-8",
    ) as f:

        for line in results:

            f.write(
                line + "\n"
            )

    print()
    print(
        f"Success: {len(results)}"
    )


if __name__ == "__main__":
    main()
