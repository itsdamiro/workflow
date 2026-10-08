#!/usr/bin/env python3
"""Where a Claude Code project's tokens go: session length, context size, and what a context cap would save.

Usage: python3 context_report.py <transcripts-dir> [--caps 150000,200000,300000] [--restart-extra 12000]

Reads the project's *.jsonl transcripts (main thread only; each message counted once by its id) and prints aggregates
only: no prompt, path or file content reaches the output. A "context" is the input a response was answered over: new,
cache-written and cache-read tokens together. Every message re-reads its whole context, so the sum of contexts is what
long sessions cost; the cap simulation restarts a session when its context passes the cap and asks what that would save.
"""

import argparse
import glob
import json
import os
import statistics as st

MIN_MESSAGES = 5


def session_contexts(path: str) -> list[int]:
    """The context of each main-thread answer in one transcript, in order; each message id counts once, one without usage not at all."""
    seen, ctx = set(), []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") != "assistant" or e.get("isSidechain"):
                continue
            m = e.get("message") or {}
            mid = m.get("id")
            if mid is not None and mid in seen:
                continue
            seen.add(mid)
            u = m.get("usage") or {}
            total = sum(u.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            if total:
                ctx.append(total)
    return ctx


def load_sessions(folder: str) -> list[list[int]]:
    """One list of per-message contexts for each session with at least MIN_MESSAGES messages."""
    contexts = (session_contexts(path) for path in sorted(glob.glob(os.path.join(folder, "*.jsonl"))))
    return [ctx for ctx in contexts if len(ctx) >= MIN_MESSAGES]


def simulate(sessions: list[list[int]], cap: int, restart: int) -> tuple[int, int]:
    """(total context tokens, restarts) if each session restarted whenever its context passed `cap`.

    A restart begins again at `restart` tokens plus what that message added; a drop in context (a compaction) adds nothing.
    """
    total = restarts = 0
    for ctx in sessions:
        cur = ctx[0]
        total += cur
        for i in range(1, len(ctx)):
            d = max(ctx[i] - ctx[i - 1], 0)
            cur += d
            if cur > cap:
                cur, restarts = restart + d, restarts + 1
            total += cur
    return total, restarts


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--caps", default="150000,200000,300000")
    ap.add_argument("--restart-extra", type=int, default=12000, help="tokens a restart adds to the baseline (the handoff read)")
    a = ap.parse_args(argv)
    sessions = load_sessions(a.folder)
    if not sessions:
        print(f"no session with at least {MIN_MESSAGES} messages in {a.folder}")
        return 1
    actual = sum(sum(s) for s in sessions)
    base = int(st.median(s[0] for s in sessions))
    biggest = sorted(max(s) for s in sessions)
    top = sorted((sum(s) for s in sessions), reverse=True)
    print(f"sessions {len(sessions)}, messages {sum(len(s) for s in sessions)}, median messages per session {int(st.median(len(s) for s in sessions))}")
    print(f"median largest context {int(st.median(biggest)):,}, maximum {biggest[-1]:,}, median first-message context {base:,}")
    print(f"context tokens re-read in all: {actual:,}; the longest 20% of sessions account for {100 * sum(top[:max(1, len(top) // 5)]) // actual}%")
    for cap in (int(c) for c in a.caps.split(",")):
        total, restarts = simulate(sessions, cap, base + a.restart_extra)
        print(f"cap {cap:>9,}: {total:,} ({100 * (actual - total) // actual}% less), {restarts} restarts")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
