"""Tests for workflows.reset() — the autostart fresh-start fix.

After a Nilsson restart, the previous run's `paused` state was being
restored by resume_paused_async, which caused workflows.start() to
return the existing (now-stale) runner instead of launching fresh.
reset() clears that state so autostart truly starts fresh.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import workflows                                                # noqa: E402
from workflows import WorkflowRunner                             # noqa: E402
from server import work_queue                                    # noqa: E402

fails: list[str] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


WF = "run_local"                                                  # exists in tree
log_path = workflows._WORKFLOWS_DIR / WF / "last_run.json"
backup = log_path.read_text() if log_path.exists() else None
orig_runner = workflows._runners.pop(WF, None)
orig_items = list(work_queue._items)

try:
    # Seed: persisted state + an in-memory runner + a queue item for the wf.
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('{"status":"paused","current_step":0,"steps":[]}')
    workflows._runners[WF] = WorkflowRunner(WF)
    workflows._runners[WF].status = "paused"
    item = work_queue.add(tool=f"workflow:{WF}", title="stale", detail_html="x")
    qid = item["id"]
    other = work_queue.add(tool="other", title="keep me")

    workflows.reset(WF)

    ok("reset removes runner from _runners", WF not in workflows._runners)
    ok("reset deletes last_run.json", not log_path.exists())
    pending_ids = {i["id"] for i in work_queue.list_pending()}
    ok("reset clears stale queue item", qid not in pending_ids)
    ok("reset leaves other queue items alone", other["id"] in pending_ids)

    # Idempotent: calling reset twice / on an unknown workflow is a no-op.
    workflows.reset(WF)
    workflows.reset("__does_not_exist__")
    ok("reset is idempotent / no-raise on unknown", True)

    # After reset, a fresh workflows.start would create a new runner —
    # we don't actually start (would launch a subprocess); just verify
    # the gate (existing runner check) no longer blocks.
    ok("post-reset: nothing blocks a fresh start",
       WF not in workflows._runners or
       workflows._runners[WF].status not in ("running", "paused"))
finally:
    # Restore original state so this test doesn't leak.
    workflows._items_cleanup_ids = [item["id"], other["id"]]
    for i_id in workflows._items_cleanup_ids:
        try:
            work_queue.remove(i_id)
        except Exception:
            pass
    work_queue._items[:] = orig_items
    work_queue._save()
    if backup is not None:
        log_path.write_text(backup)
    elif log_path.exists():
        log_path.unlink()
    workflows._runners.pop(WF, None)
    if orig_runner is not None:
        workflows._runners[WF] = orig_runner

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll workflows.reset tests passed.")
