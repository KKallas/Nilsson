#!/usr/bin/env python3
"""Embed the served project's page (iframe) into the dashboard (issue #14).

Reads the active ``run_local`` session marker (``.nilsson/run_local.json``
— written by ``workflows/run_local/step_1_start.py``), wraps that URL in
a small self-contained HTML widget with an iframe + a Refresh button, and
pushes it via the existing render-tool/artifact pattern so the chat UI's
dashboard drawer can open it.

Inputs:
  --port: int — Nilsson's port (default: env RENDER_PORT, then 8421). The
                dashboard URL printed back uses this.
  --title: str — label shown in the widget bar (default: "Project").

Process:
  1. Reads ``.nilsson/run_local.json``. If the marker is missing, prints
     a clear "no project server running — start the run_local workflow
     first" and exits non-zero (does NOT push a broken iframe).
  2. Writes a self-contained widget to ``public/charts/<id>.html`` and
     prints ``[Open in dashboard](<url>)`` — the agent passes it through.

Output: a single ``[Open in dashboard]`` markdown link, ready for the
chat UI's existing dashboard-drawer rendering."""

from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import os
import sys
import time
from pathlib import Path

SESSION_FILE = Path(".nilsson/run_local.json")


def _read_session() -> dict | None:
    """Return the run_local session marker as a dict, or None if absent/bad."""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_widget_html(url: str, title: str) -> str:
    """Self-contained dashboard widget — iframe + Refresh button + Fix A
    wait-for-ready overlay.

    Same-browser-context cross-origin embed (parent on Nilsson's port,
    iframe on the project's port) just works for embedding; cookies/state
    scope correctly to the project origin.

    Fix A (issue #9 follow-up): on first paint the project server may
    still be cold-starting (Python interp + fastapi/uvicorn imports take
    ~1-3s). A bare iframe would show "site can't be reached" until the
    browser eventually retried. Instead we probe the URL with
    ``fetch(..., {mode:'no-cors'})`` every 200ms and only set the iframe
    src once we get *any* response (opaque is fine; we just need the
    socket to be live). After ``timeoutMs`` we fail-open and load the
    iframe regardless so we never get stuck."""
    u = _html.escape(url, quote=True)
    t = _html.escape(title)
    return (
        "<!doctype html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{t}</title>"
        "<style>"
        "html,body{margin:0;height:100%;background:#0d1117;color:#c9d1d9;"
        "font-family:system-ui,sans-serif}"
        "#bar{padding:6px 10px;display:flex;align-items:center;gap:10px;"
        "background:#161b22;border-bottom:1px solid #30363d;font-size:13px}"
        "#bar a{color:#58a6ff;text-decoration:none}"
        "button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;"
        "border-radius:6px;padding:4px 12px;cursor:pointer;font-size:12px}"
        "button:hover{background:#30363d}"
        "iframe{border:0;width:100%;height:calc(100vh - 36px);display:block;"
        "background:#0d1117}"
        "#wait{position:absolute;inset:36px 0 0 0;display:flex;align-items:"
        "center;justify-content:center;flex-direction:column;gap:8px;"
        "background:#0d1117;color:#8b949e;font-size:14px}"
        "#wait.gone{display:none}"
        ".dot{width:8px;height:8px;border-radius:50%;background:#58a6ff;"
        "animation:pulse 1s ease-in-out infinite}"
        "@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}"
        "</style></head><body>"
        "<div id=\"bar\">"
        f"<span>▶ {t}</span>"
        f"<a href=\"{u}\" target=\"_blank\" rel=\"noopener\">Open in new tab ↗</a>"
        "<span style=\"flex:1\"></span>"
        "<button onclick=\"var f=document.getElementById('f');f.src=f.src\">"
        "Refresh</button>"
        "</div>"
        "<div id=\"wait\"><div class=\"dot\"></div>"
        f"<div>Starting project server… ({u})</div></div>"
        f"<iframe id=\"f\"></iframe>"
        "<script>"
        f"(function(){{var url={json.dumps(url)};"
        "var f=document.getElementById('f');"
        "var w=document.getElementById('wait');"
        "var t0=Date.now(),timeoutMs=8000;"
        "function show(){f.src=url;w.classList.add('gone');}"
        "function probe(){"
        "fetch(url,{mode:'no-cors',cache:'no-store'})"
        ".then(show)"
        ".catch(function(){"
        "if(Date.now()-t0>timeoutMs){show();}"
        "else{setTimeout(probe,200);}"
        "});"
        "}"
        "probe();"
        "}());"
        "</script>"
        "</body></html>\n"
    )


def write_artifact(html: str, *, key: str = "embed-project") -> Path:
    """Write the widget to public/charts/<id>.html and return its path.

    Mirrors tools/render/custom.py — same dashboard-artifact convention."""
    artifact_id = hashlib.md5(f"{key}{time.time()}".encode()).hexdigest()[:12]
    out_dir = Path("public/charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{artifact_id}.html"
    out.write_text(html, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed the served project (iframe) in the dashboard")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("RENDER_PORT", "8421")),
                        help="Nilsson's port for the dashboard URL")
    parser.add_argument("--title", default="Project",
                        help="label shown in the widget bar")
    args = parser.parse_args(argv)

    session = _read_session()
    if session is None:
        print("No project server running — start the run_local workflow first.",
              file=sys.stderr)
        return 1
    url = session.get("url")
    if not isinstance(url, str) or not url:
        print(f"Session marker {SESSION_FILE} is missing a usable `url`.",
              file=sys.stderr)
        return 1

    html = build_widget_html(url, args.title)
    out = write_artifact(html)
    base = f"http://127.0.0.1:{args.port}"
    print(f"[Open in dashboard]({base}/public/charts/{out.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
