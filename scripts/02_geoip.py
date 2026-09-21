import argparse
import ipaddress
import os
import geoip2.database


parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    required=True
)

parser.add_argument(
    "--output",
    required=True
)

parser.add_argument(
    "--database",
    default="GeoLite2-Country.mmdb"
)

args = parser.parse_args()


os.makedirs(
    os.path.dirname(args.output) or ".",
    exist_ok=True
)


reader = geoip2.database.Reader(
    args.database
)


count = 0


with open(
    args.input,
    "r",
    encoding="utf-8"
) as fin, open(
    args.output,
    "w",
    encoding="utf-8"
) as fout:

    for line in fin:

        ip = line.strip()

        if not ip:
            continue

        try:

            # 确保是合法 IPv4
            ipaddress.ip_address(ip)

            response = reader.country(ip)

            country = (
                response.country.iso_code
                or "XX"
            )

            country = country.upper()

        except Exception:

            country = "XX"

        fout.write(
            f"{ip}:443#{country}\n"
        )

        count += 1

        if count % 10000 == 0:

            print(
                f"{args.input}: {count}"
            )


reader.close()

print(
    f"Finished {args.input}: {count}"
)
