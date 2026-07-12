#!/usr/bin/env python3
"""Claude Code status line: context window + plan burn-rate projection.

Claude Code pipes a JSON blob to this script on stdin before each render.
Two independent meters live in there, and conflating them is the classic
mistake:

  context_window.*  -- how much the model can currently SEE. Per session.
                       Freed by /clear and /compact.
  rate_limits.*     -- how much you have SPENT against your subscription.
                       Per account. Freed only by the clock.

`rate_limits` is the only programmatic surface for plan consumption; no
slash command emits it in a pipeable form. It appears for Claude.ai
Pro/Max subscribers after the first API response of a session, and either
window may be independently absent. Handle absence, never assume presence.

Schema: https://code.claude.com/docs/en/statusline

Side effect: throttled append of each sample to ~/.claude/usage-log.jsonl,
building the history that makes week-over-week projection possible.
"""

import sys
import json
import os
import subprocess
import time

FIVE_HOURS = 5 * 3600
SEVEN_DAYS = 7 * 24 * 3600

# A pace above 1.0 is not news. Ten minutes into a window, one long request puts
# you at 3x and it means nothing. Two guards keep the alarm honest:
#
#   MIN_ELAPSED  -- say nothing until enough of the window has passed that the
#                   rate is a rate and not a single sample.
#   PACE_ALARM   -- since exhaust_fraction == 1 / pace (see pace()), a threshold
#                   of 1.15 fires only when you would run dry at 87% of the
#                   window: ~39 min early on the 5-hour, ~22 h early on the week.
#                   Below that, being "over pace" costs you nothing you'd notice.
#   PACE_WARN    -- the quiet annotation is rendered to one decimal, so anything
#                   below 1.05 would print "1.0x", which is the number that means
#                   "fine". Don't annotate what rounds to nothing. This also
#                   keeps us off the exact-1.0 boundary, where float error makes
#                   used == elapsed land on either side at random.
MIN_ELAPSED = 0.25
PACE_WARN = 1.05
PACE_ALARM = 1.15

LOG_PATH = os.path.expanduser("~/.claude/usage-log.jsonl")
STAMP_PATH = os.path.expanduser("~/.claude/.usage-log-stamp")
LOG_THROTTLE_SECONDS = 300


# --- presentation -----------------------------------------------------------

RESET = "\x1b[0m"


def paint(code, text):
    return f"\x1b[{code}m{text}{RESET}"


DIM, BOLD = "2", "1"
RED, YELLOW, GREEN, CYAN = "31", "33", "32", "36"


def severity(pct):
    """Colour by how much of a budget is gone."""
    if pct is None:
        return DIM
    if pct >= 90:
        return RED
    if pct >= 70:
        return YELLOW
    return GREEN


def bar(pct, width=10):
    if pct is None:
        return "─" * width
    filled = int(round(pct / 100 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def clock(epoch):
    return time.strftime("%a %H:%M", time.localtime(epoch))


# --- the one formula --------------------------------------------------------


def pace(used_pct, resets_at, window_seconds, now):
    """How fast are we burning, relative to the clock?

        pace = (fraction of budget spent) / (fraction of window elapsed)

    Returns (pace, exhaust_epoch). `exhaust_epoch` is populated only when the
    projection is worth acting on: enough of the window has elapsed to trust
    the rate, and the pace is high enough that running dry actually costs you
    time. Returns (None, None) when the inputs cannot support any claim.

    The projection collapses to one line. Substituting
    used/100 = pace × elapsed_fraction into

        exhaust_fraction = elapsed_fraction × (100 / used)

    gives exhaust_fraction = 1 / pace. Where you land is a function of pace
    alone -- the elapsed time cancels out entirely.
    """
    if used_pct is None or not resets_at:
        return None, None

    window_start = resets_at - window_seconds
    elapsed = now - window_start
    if elapsed <= 0 or elapsed > window_seconds:
        return None, None

    elapsed_fraction = elapsed / window_seconds
    if used_pct <= 0:
        return 0.0, None

    ratio = (used_pct / 100) / elapsed_fraction

    if elapsed_fraction < MIN_ELAPSED:
        return None, None  # too early for the rate to mean anything at all

    exhaust_at = None
    if ratio >= PACE_ALARM:
        exhaust_at = window_start + window_seconds / ratio

    return ratio, exhaust_at


def render_window(label, window, window_seconds, now):
    """One rate-limit window as a coloured segment, with projection."""
    if not window:
        return paint(DIM, f"{label} --")

    used = window.get("used_percentage")
    resets_at = window.get("resets_at")
    if used is None:
        return paint(DIM, f"{label} --")

    segment = paint(severity(used), f"{label} {used:.0f}%")

    ratio, exhaust_at = pace(used, resets_at, window_seconds, now)
    if ratio is None:
        return segment

    if exhaust_at:
        # Loud, and only when acting on it saves you something.
        segment += paint(RED, f" ▸{ratio:.1f}× dry {clock(exhaust_at)}")
    elif ratio >= PACE_WARN:
        # Over pace, but not yet enough to run dry meaningfully early.
        # Shown quietly, and never before MIN_ELAPSED has passed.
        segment += paint(YELLOW, f" ▸{ratio:.1f}×")

    return segment


# --- host CPU/RAM (shared with the Starship prompt and the SwiftBar menu bar) --


SYSUSAGE = os.path.expanduser("~/.local/bin/sysusage")


def render_sys():
    """A `cpu N% ram N%` segment from the shared sysusage script, or None.

    The prompt can't show host stats (fish/Starship isn't rendering here), so we
    ask the same script Starship and SwiftBar use. Shelling out keeps the two
    scripts decoupled; the timeout guarantees a hung read never stalls the line.
    """
    try:
        out = subprocess.run(
            [SYSUSAGE, "--json"], capture_output=True, text=True, timeout=1.0
        ).stdout
        stats = json.loads(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None

    cpu, ram = stats.get("cpu"), stats.get("ram")

    def seg(label, v):
        return paint(severity(v), f"{label} {v}%") if v is not None else None

    parts = [p for p in (seg("cpu", cpu), seg("ram", ram)) if p]
    return "  ".join(parts) if parts else None


# --- logging ----------------------------------------------------------------


def should_log(now):
    try:
        return now - os.path.getmtime(STAMP_PATH) >= LOG_THROTTLE_SECONDS
    except OSError:
        return True


def log_sample(data, now):
    """Append a throttled sample. Never let logging break the status line."""
    if not should_log(now):
        return
    try:
        rate = data.get("rate_limits") or {}
        ctx = data.get("context_window") or {}
        sample = {
            "ts": int(now),
            "session_id": data.get("session_id"),
            "model": (data.get("model") or {}).get("id"),
            "context_used_pct": ctx.get("used_percentage"),
            "five_hour": rate.get("five_hour"),
            "seven_day": rate.get("seven_day"),
        }
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(sample) + "\n")
        with open(STAMP_PATH, "w") as fh:
            fh.write(str(int(now)))
    except OSError:
        pass


# --- main -------------------------------------------------------------------


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    now = time.time()
    log_sample(data, now)

    model = (data.get("model") or {}).get("display_name", "?")
    effort = (data.get("effort") or {}).get("level")
    ctx = data.get("context_window") or {}
    rate = data.get("rate_limits") or {}

    # Line one: who am I talking to, and how hard is it thinking?
    head = paint(BOLD, model)
    if effort:
        head += paint(DIM, f" · {effort}")

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd")
    if cwd:
        head += paint(DIM, f"  {os.path.basename(cwd)}")

    # Line two: the two meters, side by side.
    ctx_pct = ctx.get("used_percentage")
    if ctx_pct is None:
        ctx_seg = paint(DIM, f"ctx {bar(None)} --")
    else:
        ctx_seg = paint(severity(ctx_pct), f"ctx {bar(ctx_pct)} {ctx_pct:.0f}%")
        if data.get("exceeds_200k_tokens"):
            ctx_seg += paint(YELLOW, " ⚠")

    five = render_window("5h", rate.get("five_hour"), FIVE_HOURS, now)
    week = render_window("wk", rate.get("seven_day"), SEVEN_DAYS, now)

    sep = paint(DIM, " · ")
    meters = [ctx_seg, five, week]
    sys_seg = render_sys()
    if sys_seg:
        meters.append(sys_seg)
    print(head)
    print(sep.join(meters))


if __name__ == "__main__":
    main()
