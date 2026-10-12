#!/usr/bin/env python3
"""One line (or one paragraph) from refresh_report.json, for the weekly pull request's title and commit message.

Usage: python tools/nations_report_summary.py [--short] data/nations/tools/refresh_report.json
"""
import json
import sys


def summary(r, short=False):
    st = r.get("status", {})
    v, s, u = st.get("verified", 0), st.get("stale", 0), st.get("unreachable", 0)
    if short:
        return f"{r.get('urls_checked', 0):,} of {r.get('urls_total', 0):,} pages, {v:,} verified, {s:,} stale, {u:,} unreachable"
    kind = "A sample run" if r.get("dry_run") or r.get("urls_checked", 0) < r.get("urls_total", 0) else "The weekly check"
    return (f"{kind} on {r.get('run_date')} read {r.get('urls_checked', 0):,} of {r.get('urls_total', 0):,} cited pages "
            f"({r.get('requests_sent', 0):,} requests, {r.get('elapsed_s', 0)} s) and tested {r.get('facts_checked', 0):,} "
            f"facts: {v:,} verified, {s:,} stale (hidden until a person restores them), {u:,} unreachable (waiting for a "
            f"person after the grace window). Changes go live only when this pull request is merged.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--short"]
    if not args:
        sys.exit(__doc__)
    print(summary(json.load(open(args[0], encoding="utf-8")), "--short" in sys.argv))
