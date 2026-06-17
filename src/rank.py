"""
rank.py — Entry point. Reads candidates.jsonl, ranks everyone, writes the
top-100 submission.csv.

Reproduce command (matches submission_metadata.yaml):
    python src/rank.py --candidates data/candidates.jsonl --out submission.csv

Design: this is a single-pass, CPU-only, no-network batch job. Each candidate is
scored independently, so it parallelises trivially and stays well inside the
5-minute / 16 GB budget. The scoring pipeline:

    final_score = fit_score
                * behavioral_availability_multiplier
                * honeypot_gate           (near-zero if internally impossible)

The semantic-embedding layer (v2) plugs in by blending a precomputed cosine
similarity into fit_score; the interface stays the same.
"""

import argparse
import csv
import json
import sys
from datetime import date

# Allow running as "python src/rank.py" without package install.
sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")

import jd
from audit import audit_candidate
from signals import availability_multiplier
from fit import score_fit
from reasoning import build_reasoning

TOP_N = 100
HONEYPOT_FLOOR = 0.001   # gate multiplier for flagged-impossible profiles


def parse_today(s):
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def iter_candidates(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def score_candidate(c, today):
    is_honeypot, hp_reasons = audit_candidate(c, today)
    fit, fit_ev = score_fit(c, today)
    avail, avail_notes = availability_multiplier(c, today)

    gate = HONEYPOT_FLOOR if is_honeypot else 1.0
    final = fit * avail * gate

    reasoning = build_reasoning(c, fit_ev, avail_notes, is_honeypot, hp_reasons)
    return {
        "candidate_id": c.get("candidate_id"),
        "score": final,
        "fit": fit,
        "avail": avail,
        "is_honeypot": is_honeypot,
        "reasoning": reasoning,
        "_tiebreak": (fit, avail),   # deterministic tiebreak before id
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True, help="path to candidates.jsonl")
    ap.add_argument("--out", default="submission.csv")
    ap.add_argument("--today", default=jd.REFERENCE_TODAY,
                    help="reference 'today' (YYYY-MM-DD) for reproducible recency")
    ap.add_argument("--top", type=int, default=TOP_N)
    args = ap.parse_args()

    today = parse_today(args.today)

    rows = []
    n = 0
    n_honeypot = 0
    for c in iter_candidates(args.candidates):
        r = score_candidate(c, today)
        n += 1
        n_honeypot += int(r["is_honeypot"])
        rows.append(r)
        if n % 20000 == 0:
            print(f"  scored {n} candidates...", file=sys.stderr)

    # Sort: score desc, then fit desc, then avail desc, then id asc (deterministic).
    rows.sort(key=lambda r: (-r["score"], -r["_tiebreak"][0],
                             -r["_tiebreak"][1], r["candidate_id"]))

    top = rows[:args.top]

    # The validator requires: for equal printed scores, candidate_id must be
    # ascending. We print 6 decimals (so genuine differences survive) and then
    # re-order any exact printed-score ties by candidate_id to satisfy the rule.
    for r in top:
        r["printed"] = f"{r['score']:.6f}"
    top.sort(key=lambda r: (-float(r["printed"]), r["candidate_id"]))

    # Sanity: how many honeypots leaked into the top 100? (must stay <10%)
    leaked = sum(1 for r in top if r["is_honeypot"])
    print(f"Scored {n} candidates ({n_honeypot} flagged honeypots). "
          f"Honeypots in top {args.top}: {leaked} "
          f"({leaked/max(1,len(top)):.1%}).", file=sys.stderr)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, r in enumerate(top, start=1):
            w.writerow([r["candidate_id"], i, r["printed"], r["reasoning"]])

    print(f"Wrote {len(top)} rows to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
