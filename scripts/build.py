#!/usr/bin/env python3
"""把 data/*.csv 合成页面数据，写进 index.html 的 <script id="spx-data">（页面是纯静态的，数据内嵌）。数据没变化就不重写页面。"""
import csv
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HTML = ROOT / "index.html"
START = "2019-10-07"


def rd(name):
    p = DATA / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    out["price"] = [[r["date"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])] for r in rd("price_spx.csv") if r["date"] >= START]
    out["es"] = [[r["date"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])] for r in rd("price_es.csv") if r["date"] >= START]
    keys = ["spx_call_vol", "spx_put_vol", "spx_call_oi", "spx_put_oi", "idx_call_vol", "idx_put_vol", "idx_call_oi", "idx_put_oi"]
    out["cboe"] = [[r["date"]] + [int(r[k]) for k in keys] for r in rd("cboe_daily.csv")]
    html = HTML.read_text(encoding="utf-8")
    old = re.search(r'<script id="spx-data">window\.SPX_DATA=(.*?);</script>', html, flags=re.S)
    if old:
        try:
            prev = json.loads(old.group(1))
            if isinstance(prev, dict) and {k: v for k, v in prev.items() if k != "updated"} == {k: v for k, v in out.items() if k != "updated"}:
                print("数据没有变化，保持页面不变。")
                return
        except ValueError:
            pass
    js = "window.SPX_DATA=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + ";"
    new, n = re.subn(r'(<script id="spx-data">).*?(</script>)', lambda m: m.group(1) + js + m.group(2), html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('index.html 里没找到 <script id="spx-data">')
    HTML.write_text(new, encoding="utf-8")
    print(f"【成功】已写入 index.html：指数 {len(out['price'])} 天，ES {len(out['es'])} 天，期权 {len(out['cboe'])} 天")


if __name__ == "__main__":
    main()
