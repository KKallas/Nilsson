#!/usr/bin/env python3
"""examples/minesweeper/app.py — the bundled default starter project.

Nilsson ships this as the default project served by ``workflows/run_local``:
when you start Nilsson with no ``project`` block configured, it auto-defaults
to launching this app on port 7700, so the first thing you see is a working
example, not an empty shell. Replace it any time by editing
``.nilsson/config.json`` ``project`` (see ``examples/project.config.json``).

There is no venv bootstrap here on purpose: Nilsson already manages a
virtualenv with this app's dependencies (``fastapi``/``uvicorn``/
``python-multipart``/``segno``). The original standalone repo did its own
bootstrap; under Nilsson that's redundant.

All game rules live in ``game.py`` (pure + unit-tested via
``tests/test_game.py``). This file only adds the network, the per-click
5-second pending-open timers, the QR, and admin.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import secrets
import socket
import sys
import time
from pathlib import Path

import segno
import uvicorn
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from game import Game, PENDING_SECONDS                      # noqa: E402

PORT = int(os.environ.get("PORT", "7700"))
ADMIN_FILE = ROOT / "admin.json"

app = FastAPI()
GAME = Game()
SOCKETS: dict[WebSocket, str] = {}
_pending_tasks: dict[tuple[int, int], asyncio.Task] = {}


# ---- helpers --------------------------------------------------------
def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def is_lan(host: str) -> bool:
    """LAN-only admin: loopback + RFC1918 only; everything else refused."""
    if host in ("127.0.0.1", "::1", "localhost"):
        return True
    p = host.split(".")
    if len(p) == 4 and all(x.isdigit() for x in p):
        a, b = int(p[0]), int(p[1])
        return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)
    return False


def state_for(pid: str) -> dict:
    v = GAME.view(pid)
    now = time.time()
    v["pending"] = [
        {"r": r, "c": c, "by_me": info["by"] == pid,
         "left": max(0.0, round(info["deadline"] - now, 1))}
        for (r, c), info in GAME.pending.items()
    ]
    return v


async def broadcast() -> None:
    dead = []
    for ws, pid in list(SOCKETS.items()):
        try:
            await ws.send_json(state_for(pid))
        except Exception:
            dead.append(ws)
    for ws in dead:
        SOCKETS.pop(ws, None)


async def _pending_timer(r: int, c: int) -> None:
    await asyncio.sleep(PENDING_SECONDS)
    if (r, c) in GAME.pending:
        GAME.resolve_pending(r, c)
    _pending_tasks.pop((r, c), None)
    await broadcast()


# ---- pages ----------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def game_page(request: Request):
    resp = HTMLResponse((ROOT / "static" / "index.html").read_text())
    if not request.cookies.get("pid"):
        resp.set_cookie("pid", secrets.token_hex(8), max_age=86400)
    return resp


@app.get("/qr", response_class=HTMLResponse)
def qr_page():
    url = f"http://{lan_ip()}:{PORT}/"
    return (f'<!doctype html><meta charset=utf-8><title>Join</title>'
            f'<body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;'
            f'text-align:center;padding-top:6vh">'
            f'<h2>Scan to join on your network</h2>'
            f'<img src="/qr.png" width="320" '
            f'style="background:#fff;padding:16px;border-radius:12px">'
            f'<p style="font-size:20px">{url}</p>'
            f'<p style="color:#8b949e">Same Wi-Fi/LAN only. '
            f'Remote = use a VPN.</p>')


@app.get("/qr.png")
def qr_png():
    out = io.BytesIO()
    segno.make(f"http://{lan_ip()}:{PORT}/").save(out, kind="png", scale=8)
    return Response(out.getvalue(), media_type="image/png")


# ---- admin (LAN-only) ----------------------------------------------
def _admin_load() -> dict:
    return json.loads(ADMIN_FILE.read_text()) if ADMIN_FILE.exists() else {}


def _hash(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode()).hexdigest()


def _guard(request: Request) -> str | None:
    host = request.client.host if request.client else ""
    if not is_lan(host):
        return ("<h3>Admin is local-network only.</h3>"
                "<p>Connect via the LAN or a VPN into it.</p>")
    return None


@app.get("/admin", response_class=HTMLResponse)
def admin_get(request: Request):
    if (blocked := _guard(request)):
        return HTMLResponse(blocked, status_code=403)
    cfg = _admin_load()
    if not cfg:
        return HTMLResponse(
            '<h2>Set admin password</h2><form method=post action=/admin/setpw>'
            '<input name=pw type=password placeholder="new password" required>'
            '<button>Set</button></form>')
    if request.cookies.get("admin") != cfg.get("token"):
        return HTMLResponse(
            '<h2>Admin login</h2><form method=post action=/admin/login>'
            '<input name=pw type=password required><button>Log in</button></form>')
    g = GAME
    return HTMLResponse(
        f'<h2>Admin</h2><p>Players: '
        f'{", ".join(p.name for p in g.players.values()) or "none"} — '
        f'status {g.status}</p>'
        f'<form method=post action=/admin/reset>'
        f'<label>W <input name=w value={g.w} size=3></label> '
        f'<label>H <input name=h value={g.h} size=3></label> '
        f'<label>Mines <input name=mines value={g.n_mines} size=4></label> '
        f'<button>Reset match</button></form>')


@app.post("/admin/setpw")
def admin_setpw(request: Request, pw: str = Form(...)):
    if _guard(request) or _admin_load():
        return RedirectResponse("/admin", 303)
    salt, token = secrets.token_hex(8), secrets.token_hex(16)
    ADMIN_FILE.write_text(json.dumps(
        {"salt": salt, "hash": _hash(pw, salt), "token": token}))
    r = RedirectResponse("/admin", 303)
    r.set_cookie("admin", token, max_age=86400)
    return r


@app.post("/admin/login")
def admin_login(request: Request, pw: str = Form(...)):
    if _guard(request):
        return RedirectResponse("/admin", 303)
    cfg = _admin_load()
    r = RedirectResponse("/admin", 303)
    if cfg and _hash(pw, cfg["salt"]) == cfg["hash"]:
        r.set_cookie("admin", cfg["token"], max_age=86400)
    return r


@app.post("/admin/reset")
async def admin_reset(request: Request, w: int = Form(16), h: int = Form(16),
                      mines: int = Form(40)):
    cfg = _admin_load()
    if _guard(request) or request.cookies.get("admin") != cfg.get("token"):
        return RedirectResponse("/admin", 303)
    w, h = max(5, min(40, w)), max(5, min(40, h))
    mines = max(1, min(w * h - 1, mines))
    GAME.reset(w, h, mines)
    for t in _pending_tasks.values():
        t.cancel()
    _pending_tasks.clear()
    await broadcast()
    return RedirectResponse("/admin", 303)


# ---- realtime -------------------------------------------------------
@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    pid = sock.query_params.get("pid") or secrets.token_hex(8)
    SOCKETS[sock] = pid
    try:
        while True:
            msg = await sock.receive_json()
            t = msg.get("t")
            if t == "join":
                GAME.add_player(pid, (msg.get("name") or "Player")[:16])
            elif t == "click":
                r, c = int(msg["r"]), int(msg["c"])
                GAME.click(pid, r, c)
                if (r, c) in GAME.pending and (r, c) not in _pending_tasks:
                    _pending_tasks[(r, c)] = asyncio.create_task(
                        _pending_timer(r, c))
            elif t == "flag":
                GAME.flag(pid, int(msg["r"]), int(msg["c"]))
            elif t == "arm":
                GAME.arm(pid, int(msg["k"]))
            await broadcast()
    except WebSocketDisconnect:
        SOCKETS.pop(sock, None)


def main() -> None:
    url = f"http://{lan_ip()}:{PORT}"
    print(f"[minesweeper] Game: {url}/   Join: {url}/qr   "
          f"Admin: {url}/admin (LAN-only)", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
