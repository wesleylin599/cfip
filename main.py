import ipaddress
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# 配置
# ============================================================

DOMAIN = "api.090227.xyz"
PORT = 443

# 并发数
WORKERS = 64

# curl 超时
CONNECT_TIMEOUT = 2
MAX_TIME = 5

# 输入 / 输出
CIDR_FILE = "cidr.txt"

# 探测结果直接覆盖发布列表 ips.txt
OUTPUT_FILE = "ips.txt"
FAILED_FILE = "cidrip_failed.txt"


# ============================================================
# Cloudflare Colo -> 国家代码
# ============================================================

COLO_COUNTRY = {

    # --------------------------------------------------------
    # Asia
    # --------------------------------------------------------
    "HKG": "HK",
    "TPE": "TW",
    "KHH": "TW",

    "ICN": "KR",
    "SEL": "KR",

    "NRT": "JP",
    "KIX": "JP",
    "NGO": "JP",
    "FUK": "JP",

    "SIN": "SG",

    "BKK": "TH",

    "KUL": "MY",

    "CGK": "ID",

    "MNL": "PH",

    "DEL": "IN",
    "BOM": "IN",
    "BLR": "IN",
    "MAA": "IN",
    "HYD": "IN",

    "DAC": "BD",

    # --------------------------------------------------------
    # Europe
    # --------------------------------------------------------
    "AMS": "NL",
    "RTM": "NL",

    "LHR": "GB",
    "MAN": "GB",

    "FRA": "DE",
    "MUC": "DE",
    "DUS": "DE",
    "HAM": "DE",

    "CDG": "FR",
    "MRS": "FR",

    "MAD": "ES",
    "BCN": "ES",

    "LIS": "PT",

    "DUB": "IE",

    "BRU": "BE",

    "ZRH": "CH",
    "GVA": "CH",

    "VIE": "AT",

    "CPH": "DK",

    "OSL": "NO",

    "ARN": "SE",

    "HEL": "FI",

    "WAW": "PL",

    "PRG": "CZ",

    "BUD": "HU",

    "OTP": "RO",

    "SOF": "BG",

    "ATH": "GR",

    "IST": "TR",

    "KIV": "MD",

    "RIX": "LV",

    "VNO": "LT",

    "TLL": "EE",

    "KBP": "UA",

    "SVO": "RU",
    "LED": "RU",

    # --------------------------------------------------------
    # North America
    # --------------------------------------------------------
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
    "JFK": "US",
    "EWR": "US",
    "BOS": "US",
    "MSP": "US",
    "DTW": "US",
    "CLT": "US",
    "PHL": "US",
    "DCA": "US",
    "STL": "US",
    "BNA": "US",
    "AUS": "US",
    "SAT": "US",
    "MCI": "US",
    "IND": "US",
    "CLE": "US",
    "CMH": "US",
    "PIT": "US",
    "RDU": "US",
    "TPA": "US",
    "ORF": "US",
    "SLC": "US",
    "OAK": "US",
    "SMF": "US",
    "SAN": "US",

    "YYZ": "CA",
    "YUL": "CA",
    "YVR": "CA",
    "YYC": "CA",

    # --------------------------------------------------------
    # South America
    # --------------------------------------------------------
    "GRU": "BR",
    "GIG": "BR",
    "EZE": "AR",
    "SCL": "CL",
    "LIM": "PE",
    "BOG": "CO",
    "UIO": "EC",

    # --------------------------------------------------------
    # Oceania
    # --------------------------------------------------------
    "SYD": "AU",
    "MEL": "AU",
    "BNE": "AU",
    "PER": "AU",
    "ADL": "AU",

    "AKL": "NZ",

    # --------------------------------------------------------
    # Middle East
    # --------------------------------------------------------
    "DXB": "AE",
    "AUH": "AE",

    "DOH": "QA",

    "RUH": "SA",
    "JED": "SA",

    "TLV": "IL",

    "AMM": "JO",

    # --------------------------------------------------------
    # Africa
    # --------------------------------------------------------
    "JNB": "ZA",
    "CPT": "ZA",

    "NBO": "KE",

    "CAI": "EG",

    # --------------------------------------------------------
    # Other
    # --------------------------------------------------------
    "LOS": "NG",
}


# ============================================================
# 读取 CIDR
# ============================================================

def expand_cidr(filename):
    ips = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 跳过注释
            if line.startswith("#"):
                continue

            try:
                network = ipaddress.ip_network(
                    line,
                    strict=False
                )
            except ValueError:
                print(f"[INVALID CIDR] {line}")
                continue

            # 只处理 IPv4
            if network.version != 4:
                print(f"[SKIP IPv6] {line}")
                continue

            # hosts() 不包含 network / broadcast
            for ip in network.hosts():
                ips.append(str(ip))

    return ips


# ============================================================
# 探测单个 IP
# ============================================================

def probe(ip):

    cmd = [
        "curl",

        # 静默，但保留错误信息
        "-sS",

        # 不使用系统代理
        "--noproxy", "*",

        # TCP 连接超时
        "--connect-timeout", str(CONNECT_TIMEOUT),

        # 整体超时
        "--max-time", str(MAX_TIME),

        # 强制：
        # api.090227.xyz:443 -> 指定 IP
        "--resolve",
        f"{DOMAIN}:{PORT}:{ip}",

        # 输出响应头
        "-D",
        "-",

        # trace
        f"https://{DOMAIN}/cdn-cgi/trace",
    ]

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_TIME + 3,
        )

        stdout = result.stdout
        stderr = result.stderr.strip()

        # ====================================================
        # 1. 优先读取 colo=
        #
        # 正常情况下：
        #
        # colo=AMS
        # ====================================================

        match = re.search(
            r"^colo=([A-Z0-9]{3})$",
            stdout,
            re.MULTILINE,
        )

        if match:

            colo = match.group(1).upper()

            country = COLO_COUNTRY.get(colo)

            if country:

                return {
                    "ip": ip,
                    "status": "OK",
                    "colo": colo,
                    "country": country,
                    "error": "",
                }

            return {
                "ip": ip,
                "status": "UNKNOWN_COLO",
                "colo": colo,
                "country": None,
                "error": "",
            }

        # ====================================================
        # 2. colo 没有拿到
        #
        # 例如：
        #
        # HTTP/2 403
        # cf-ray: a601f1f73e9afddf-SIN
        #
        # 从 cf-ray 获取 PoP
        #
        # 注意：HTTP/2 的头名一律小写（cf-ray:），
        # 只有 HTTP/1.1 才是 CF-RAY:，必须忽略大小写。
        # ====================================================

        match = re.search(
            r"^cf-ray:\s*[a-f0-9]+-([a-z0-9]{3})\s*$",
            stdout,
            re.MULTILINE | re.IGNORECASE,
        )

        if match:

            colo = match.group(1).upper()

            country = COLO_COUNTRY.get(colo)

            if country:

                return {
                    "ip": ip,
                    "status": "CF_RAY",
                    "colo": colo,
                    "country": country,
                    "error": "",
                }

            return {
                "ip": ip,
                "status": "UNKNOWN_COLO",
                "colo": colo,
                "country": None,
                "error": "",
            }

        # ====================================================
        # 3. curl 本身失败
        # ====================================================

        if result.returncode != 0:

            return {
                "ip": ip,
                "status": "CURL_ERROR",
                "colo": None,
                "country": None,
                "error": stderr[:500],
            }

        # ====================================================
        # 4. HTTP 有响应，但是没有 colo / CF-RAY
        # ====================================================

        return {
            "ip": ip,
            "status": "NO_COLO",
            "colo": None,
            "country": None,
            "error": stdout[:500],
        }

    except subprocess.TimeoutExpired:

        return {
            "ip": ip,
            "status": "TIMEOUT",
            "colo": None,
            "country": None,
            "error": "curl timeout",
        }

    except Exception as e:

        return {
            "ip": ip,
            "status": "EXCEPTION",
            "colo": None,
            "country": None,
            "error": str(e),
        }


# ============================================================
# 主程序
# ============================================================

def main():

    print("=" * 70)
    print("Cloudflare IP -> Colo -> Country")
    print("=" * 70)

    print(f"Domain       : {DOMAIN}")
    print(f"Workers      : {WORKERS}")
    print(f"Connect time : {CONNECT_TIMEOUT}s")
    print(f"Max time     : {MAX_TIME}s")
    print()

    # --------------------------------------------------------
    # 读取 IP
    # --------------------------------------------------------

    print(f"[*] Reading {CIDR_FILE} ...")

    ips = expand_cidr(CIDR_FILE)

    total = len(ips)

    print(f"[*] Total IPv4 : {total}")
    print()

    if total == 0:
        print("[ERROR] No IPv4 address found.")
        return

    # --------------------------------------------------------
    # 统计
    # --------------------------------------------------------

    success = 0
    cf_ray = 0
    unknown_colo = 0
    failed = 0

    # 保存结果
    output_lines = []
    failed_lines = []

    # --------------------------------------------------------
    # 并发探测
    # --------------------------------------------------------

    print("[*] Starting probes...")
    print()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:

        futures = {
            executor.submit(probe, ip): ip
            for ip in ips
        }

        for done, future in enumerate(
            as_completed(futures),
            1
        ):

            ip = futures[future]

            try:
                result = future.result()

            except Exception as e:

                result = {
                    "ip": ip,
                    "status": "EXCEPTION",
                    "colo": None,
                    "country": None,
                    "error": str(e),
                }

            status = result["status"]
            colo = result["colo"]
            country = result["country"]

            # =================================================
            # 成功
            # =================================================

            if country:

                if status == "OK":
                    success += 1

                elif status == "CF_RAY":
                    cf_ray += 1

                output_lines.append(
                    f"{ip}:443#{country}"
                )

                print(
                    f"[{done}/{total}] "
                    f"{ip} -> "
                    f"{colo} -> "
                    f"{country} "
                    f"[{status}]"
                )

            # =================================================
            # Colo 未知
            # =================================================

            elif status == "UNKNOWN_COLO":

                unknown_colo += 1

                print(
                    f"[{done}/{total}] "
                    f"{ip} -> "
                    f"{colo} -> UNKNOWN_COLO"
                )

                failed_lines.append(
                    f"{ip}\t{status}\t{colo or '-'}"
                )

            # =================================================
            # 失败
            # =================================================

            else:

                failed += 1

                error = result.get("error", "")

                # 只显示一行
                error = error.replace(
                    "\r", " "
                ).replace(
                    "\n", " "
                )

                if len(error) > 120:
                    error = error[:120]

                print(
                    f"[{done}/{total}] "
                    f"{ip} -> "
                    f"{status}"
                    + (
                        f" | {error}"
                        if error
                        else ""
                    )
                )

                failed_lines.append(
                    f"{ip}\t{status}\t{error}"
                )

    # --------------------------------------------------------
    # 写成功结果
    # --------------------------------------------------------

    print()
    print("[*] Writing results...")

    # 按 IP 数值排序，保证 ips.txt 输出稳定
    output_lines.sort(
        key=lambda line: tuple(
            int(part)
            for part in line.split(":", 1)[0].split(".")
        )
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        for line in output_lines:
            f.write(line + "\n")

    # --------------------------------------------------------
    # 写失败结果
    # --------------------------------------------------------

    with open(
        FAILED_FILE,
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        for line in failed_lines:
            f.write(line + "\n")

    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)

    print(f"Total       : {total}")
    print(f"colo=       : {success}")
    print(f"CF-RAY      : {cf_ray}")
    print(f"Unknown colo: {unknown_colo}")
    print(f"Failed      : {failed}")

    print()
    print(f"Output      : {OUTPUT_FILE}")
    print(f"Failed list : {FAILED_FILE}")
    print()

    print("=" * 70)


if __name__ == "__main__":
    main()