#!/usr/bin/env python3
"""从 Yahoo Finance 抓标普 500 指数（^GSPC）日线，写入 data/price_spx.csv（date,open,high,low,close）。失败只告警、保留旧文件。"""
import csv
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=10y&interval=1d"


def fetch():
    for attempt in range(4):
        try:
            out = subprocess.run(["curl", "-s", "-m", "40", "-A", "Mozilla/5.0", URL], capture_output=True, check=True).stdout
            return json.loads(out.decode("utf-8"))["chart"]["result"][0]
        except Exception:                                      # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def main() -> None:
    DATA.mkdir(exist_ok=True)
    try:
        res = fetch()
        off, q = res["meta"]["gmtoffset"], res["indicators"]["quote"][0]
        rows = {}
        for i, t in enumerate(res["timestamp"]):
            if None in (q["open"][i], q["high"][i], q["low"][i], q["close"][i]):
                continue
            d = dt.datetime.fromtimestamp(t + off, dt.timezone.utc).date().isoformat()
            rows.setdefault(d, (d, round(q["open"][i], 2), round(q["high"][i], 2), round(q["low"][i], 2), round(q["close"][i], 2)))
        rows = sorted(rows.values())
        if len(rows) < 1000:
            raise ValueError(f"只取到 {len(rows)} 行，疑似异常")
        with (DATA / "price_spx.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "open", "high", "low", "close"])
            w.writerows(rows)
        print(f"【成功】^GSPC -> price_spx.csv：{len(rows)} 行，{rows[0][0]} ~ {rows[-1][0]}")
    except Exception as e:                                      # noqa: BLE001
        print(f"【警告】^GSPC 抓取失败，保留旧文件：{e}", file=sys.stderr)


if __name__ == "__main__":
    main()
