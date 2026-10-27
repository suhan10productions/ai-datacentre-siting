"""Download the PeeringDB facility list used in the paper.

PeeringDB's Acceptable Use Policy does not allow its data to be
redistributed in bulk without permission, so the facility records are not
included in this package. This script downloads them directly for your own
research use. The paper used the list as it stood on 14 October 2026.
data/peeringdb_ids_2026-10-14.csv lists the facility IDs used (IDs only, no
records). With --ids, the script downloads exactly those facilities, so the
facility set matches the paper's; records edited in PeeringDB since that date
(for example moved coordinates) can still differ slightly.

Usage:
    python fetch_peeringdb.py data/peeringdb_fac.csv --ids data/peeringdb_ids_2026-10-14.csv
    python fetch_peeringdb.py data/peeringdb_fac.csv          (current live list)
Then run join.py (with the Aqueduct 4.0 geodatabase) to create
data/peeringdb_water.csv, which siting_analysis.py reads.
"""
import csv
import json
import sys
import urllib.request

URL = "https://www.peeringdb.com/api/fac?status=ok"
FIELDS = ["id", "org_name", "name", "city", "state", "country", "region_continent",
          "latitude", "longitude", "created", "updated", "net_count", "ix_count", "status"]

args = sys.argv[1:]
ids_file = None
if "--ids" in args:
    i = args.index("--ids"); ids_file = args[i + 1]; del args[i:i + 2]
out = args[0] if args else "data/peeringdb_fac.csv"
if ids_file:
    with open(ids_file, encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip().isdigit()]
    data = []
    for k in range(0, len(ids), 150):
        url = "https://www.peeringdb.com/api/fac?id__in=" + ",".join(ids[k:k + 150])
        with urllib.request.urlopen(url, timeout=120) as r:
            data += json.load(r)["data"]
    missing = len(ids) - len(data)
    if missing:
        print(f"note: {missing} facilities in the ID list are no longer available from PeeringDB")
else:
    with urllib.request.urlopen(URL, timeout=120) as r:
        data = json.load(r)["data"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    for row in data:
        w.writerow(row)
print(f"wrote {len(data)} facilities to {out}")
