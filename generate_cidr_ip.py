#!/usr/bin/env python3

import ipaddress
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


CIDR_FILE = "cidr.txt"
OUTPUT_FILE = "cidrip.txt"

# 并发数量
MAX_WORKERS = 20

# 每个 IP 查询失败后的重试次数
RETRIES = 3

# 请求超时
TIMEOUT = 10

# 国家查询 API
API_URL = "https://ipwho.is/{ip}"


def load_cidrs():
    """读取 cidr.txt"""
    networks = []

    if not os.path.exists(CIDR_FILE):
        print(f"错误：找不到 {CIDR_FILE}")
        sys.exit(1)

    with open(CIDR_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            # 支持 # 注释
            if line.startswith("#"):
                continue

            try:
                network = ipaddress.ip_network(line, strict=False)

                # 当前只处理 IPv4
                if network.version == 4:
                    networks.append(network)
                else:
                    print(f"跳过 IPv6: {network}")

            except ValueError:
                print(f"无效 CIDR，跳过: {line}")

    return networks


def expand_ips(networks):
    """展开 CIDR 为 IP"""
    ips = []

    for network in networks:
        print(f"展开: {network} -> {network.num_addresses} 个地址")

        for ip in network.hosts():
            ips.append(str(ip))

    return ips


def get_country(ip):
    """查询 IP 国家"""
    url = API_URL.format(ip=ip)

    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "GitHub-CIDR-IP-Country/1.0"
                }
            )

            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("success") is False:
                return ip, "XX"

            country = data.get("country_code")

            if country:
                return ip, country.upper()

            return ip, "XX"

        except Exception as e:
            if attempt < RETRIES - 1:
                time.sleep(1)

    return ip, "XX"


def main():
    networks = load_cidrs()

    if not networks:
        print("没有找到有效的 IPv4 CIDR")
        sys.exit(1)

    ips = expand_ips(networks)

    print()
    print(f"CIDR 数量: {len(networks)}")
    print(f"IP 数量:   {len(ips)}")
    print()

    results = []

    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(get_country, ip): ip
            for ip in ips
        }

        for future in as_completed(futures):
            ip, country = future.result()

            results.append((ip, country))

            completed += 1

            if completed % 50 == 0 or completed == len(ips):
                print(
                    f"进度: {completed}/{len(ips)} "
                    f"({completed / len(ips) * 100:.1f}%)"
                )

    # IP 排序
    results.sort(
        key=lambda x: ipaddress.ip_address(x[0])
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ip, country in results:
            f.write(f"{ip}:443#{country}\n")

    print()
    print(f"完成：{OUTPUT_FILE}")
    print(f"共生成 {len(results)} 条")


if __name__ == "__main__":
    main()
