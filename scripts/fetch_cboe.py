#!/usr/bin/env python3
"""下载 CBOE 每日期权市场统计（每个交易日一份 JSON，2019-10-07 起），提取 标普 500 期权（SPX + SPXW）和 指数期权（全部指数期权合计）的
看涨/看跌 成交量与持仓量，增量写入 data/cboe_daily.csv。已有的日期不再下载；周末、假日没有文件（403/404）自动跳过。
  python scripts/fetch_cboe.py            增量更新（只补缺的日子）
  python scripts/fetch_cboe.py --full     从头重新下载
"""
import csv
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "cboe_daily.csv"
URL = "https://cdn.cboe.com/data/us/options/market_statistics/daily/{d}_daily_options"
START = dt.date(2019, 10, 7)
FIELDS = ["date", "spx_call_vol", "spx_put_vol", "spx_call_oi", "spx_put_oi", "idx_call_vol", "idx_put_vol", "idx_call_oi", "idx_put_oi"]


def one(d: dt.date):
    """返回 (日期, 行字典) ；没有文件返回 None；网络异常抛出。"""
    from curl_cffi import requests
    for attempt in range(3):
        try:
            r = requests.get(URL.format(d=d.isoformat()), impersonate="chrome120", timeout=40)
            break
        except Exception:                                       # noqa: BLE001
            if attempt == 2:
                raise
    if r.status_code in (403, 404):
        return None
    r.raise_for_status()
    j = json.loads(r.text)

    def pick(*keys):
        for k in keys:
            if k in j:
                v = {x["name"]: x for x in j[k]}
                return v["VOLUME"], v["OPEN INTEREST"]
        raise KeyError(keys)
    sv, so = pick("SPX + SPXW", "SPX")
    iv, io = pick("INDEX OPTIONS")
    return {"date": d.isoformat(), "spx_call_vol": sv["call"], "spx_put_vol": sv["put"], "spx_call_oi": so["call"], "spx_put_oi": so["put"],
            "idx_call_vol": iv["call"], "idx_put_vol": iv["put"], "idx_call_oi": io["call"], "idx_put_oi": io["put"]}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    have = {}
    if OUT.exists() and "--full" not in sys.argv:
        with OUT.open(encoding="utf-8") as f:
            have = {r["date"]: r for r in csv.DictReader(f)}
    today = dt.date.today()
    days = [START + dt.timedelta(days=i) for i in range((today - START).days + 1)]
    todo = [d for d in days if d.weekday() < 5 and d.isoformat() not in have]
    # 只补缺的日子；最近 3 天的数据可能当天还没出齐，重新取一遍
    todo += [d for d in days if d.weekday() < 5 and d.isoformat() in have and (today - d).days <= 3]
    print(f"需要请求 {len(todo)} 天")
    n_new, errs = 0, 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for d, res in zip(todo, ex.map(lambda x: _safe(x), todo)):
            if res == "ERR":
                errs += 1
            elif res:
                have[res["date"]] = {k: res[k] for k in FIELDS}
                n_new += 1
    if not have:
        raise SystemExit("没有取到任何数据")
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k in sorted(have):
            w.writerow(have[k])
    print(f"【成功】写入/更新 {n_new} 天，合计 {len(have)} 天，{min(have)} ~ {max(have)}；请求失败 {errs} 次")


def _safe(d):
    try:
        return one(d)
    except Exception as e:                                      # noqa: BLE001
        print(d, "失败：", e, file=sys.stderr)
        return "ERR"


if __name__ == "__main__":
    main()
