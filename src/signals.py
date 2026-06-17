"""
signals.py — Behavioral availability multiplier.

The JD is explicit: "a perfect-on-paper candidate who hasn't logged in for 6
months and has a 5% recruiter response rate is, for hiring purposes, not actually
available. Down-weight them appropriately."

So behavioral signals are NOT added to the fit score — they MULTIPLY it, acting
like a dimmer switch that dims hard-to-reach candidates. We deliberately use only
the handful of signals that actually predict "can we hire this person", and we
ignore vanity metrics (connection_count, profile_views) that measure popularity,
not hireability. Being able to justify that choice is a Stage-5 interview point.

Returns a multiplier in roughly [0.3, 1.05] plus a short explanation.
"""

from datetime import date

from jd import BEHAVIORAL


def _parse_date(s):
    if not s:
        return None
    try:
        y, m, d = str(s)[:10].split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def availability_multiplier(c, today):
    """Return (multiplier, notes:list[str])."""
    s = c.get("redrob_signals", {}) or {}
    notes = []

    # 1. Recency of activity -------------------------------------------------
    last_active = _parse_date(s.get("last_active_date"))
    if last_active:
        days = (today - last_active).days
        if days <= BEHAVIORAL["active_recent_days"]:
            recency = 1.0
        elif days >= BEHAVIORAL["stale_days"]:
            recency = 0.45
            notes.append(f"inactive {days}d")
        else:
            # linear ramp between active_recent and stale
            span = BEHAVIORAL["stale_days"] - BEHAVIORAL["active_recent_days"]
            recency = 1.0 - 0.55 * ((days - BEHAVIORAL["active_recent_days"]) / span)
    else:
        recency = 0.7

    # 2. Recruiter responsiveness -------------------------------------------
    rr = s.get("recruiter_response_rate")
    if rr is None:
        response = 0.75
    else:
        # 0% -> 0.5, 50% -> ~0.85, 100% -> 1.0  (don't fully zero people out)
        response = 0.5 + 0.5 * rr
        if rr < 0.1:
            notes.append(f"low response rate {rr:.0%}")

    # 3. Open to work --------------------------------------------------------
    open_flag = 1.0 if s.get("open_to_work_flag") else 0.8
    if not s.get("open_to_work_flag"):
        notes.append("not marked open-to-work")

    # 4. Follow-through (shows up to interviews) -----------------------------
    icr = s.get("interview_completion_rate")
    follow = 0.85 + 0.15 * icr if icr is not None else 0.95

    # 5. Notice period (JD prefers <30d, can buy out 30, >90 raises the bar) --
    notice = s.get("notice_period_days")
    if notice is None:
        notice_factor = 0.95
    elif notice <= BEHAVIORAL["preferred_notice_days"]:
        notice_factor = 1.0
    elif notice <= BEHAVIORAL["max_reasonable_notice_days"]:
        notice_factor = 0.9
    else:
        notice_factor = 0.8
        notes.append(f"{notice}d notice")

    # Geometric-style blend so no single factor dominates, then a gentle floor.
    mult = (recency * response * open_flag * follow * notice_factor) ** 0.5
    # Small bonus for verified + open candidates who are genuinely reachable.
    if s.get("verified_email") and s.get("verified_phone") and s.get("open_to_work_flag"):
        mult = min(1.05, mult * 1.03)

    mult = max(0.30, min(1.05, mult))
    return mult, notes
