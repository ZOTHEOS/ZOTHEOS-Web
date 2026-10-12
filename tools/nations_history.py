#!/usr/bin/env python3
"""Record a verifier run in data/nations/verify/history.json (newest first, 52 kept), read by the build for the
verification panel and page (DESIGN_NATIONS 9.3, 9.4).

A run that checked every URL and wrote nations.json is a full check; its "published" date is its run date, because
the history file travels in the same pull request as the data and so goes live only when that request is merged.
A capped (--limit) or dry run is a sample: "sample": true, "published": null, and it never counts as a full check.

Usage: python tools/nations_history.py --append data/nations/tools/refresh_report.json
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data", "nations", "verify", "history.json")
KEEP = 52


def entry(report):
    st = report.get("status", {})
    sample = bool(report.get("dry_run")) or report.get("urls_checked", 0) < report.get("urls_total", 0)
    return {"run_date": report["run_date"], "sample": sample, "urls_checked": report.get("urls_checked", 0),
            "urls_total": report.get("urls_total", 0), "facts_checked": report.get("facts_checked", 0),
            "verified": st.get("verified", 0), "stale": st.get("stale", 0), "unreachable": st.get("unreachable", 0),
            "elapsed_s": report.get("elapsed_s"), "published": None if sample else report["run_date"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--append", required=True, help="refresh_report.json written by nations_refresh.py")
    ap.add_argument("--history", default=HIST)
    a = ap.parse_args(argv)
    report = json.load(open(a.append, encoding="utf-8"))
    hist = json.load(open(a.history, encoding="utf-8")) if os.path.isfile(a.history) else []
    e = entry(report)
    hist = [h for h in hist if not (h["run_date"] == e["run_date"] and h.get("sample") == e["sample"])]
    hist.insert(0, e)
    hist.sort(key=lambda h: h["run_date"], reverse=True)
    hist = hist[:KEEP]
    with open(a.history, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join("  " + json.dumps(h, ensure_ascii=False) for h in hist) + "\n]\n")
    kind = "sample" if e["sample"] else "full check"
    print(f"history: recorded the {kind} of {e['run_date']} ({e['urls_checked']} of {e['urls_total']} pages); {len(hist)} runs kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
