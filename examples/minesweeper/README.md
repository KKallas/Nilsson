# Minesweeper Arena

A self-contained 1v1 multiplayer minesweeper. One file to run, no build
step, plays over your local network. Also the **ultra-simple tutorial** for
the "server-authoritative game + LAN QR + first-run admin" pattern.

## Run it

```bash
python app.py
```

First run creates a local virtualenv, installs deps, and relaunches itself
(the same trick Nilsson uses — nothing to install by hand). Then it opens a
**game window** and a **QR window** and prints:

```
Game : http://<your-LAN-IP>:7700/
Join : http://<your-LAN-IP>:7700/qr
Admin: http://<your-LAN-IP>:7700/admin   (LAN-only)
```

A second player scans the QR (same Wi-Fi/LAN) and is in. Set the port with
`PORT=8000 python app.py`.

## Rules

- **1v1, shared board**, server-authoritative (the server is the only source
  of truth; clients just draw it).
- **Open a box**: tap it. The open is *pending for 5 seconds* — your
  **opponent can tap that same box to cancel it** (it stays closed, no
  score; you just lost the tempo). You cannot cancel your own.
- **Sudden death**: if a pending open resolves onto a mine, the match ends
  immediately and the **other** player wins. If instead every safe box gets
  opened, the match ends and whoever has more correct flags wins.
- **Flags** are instant, final, and yours — they cannot be challenged. Your
  score = your flags that sit on a mine.
- **Mobile / touch**: tap the **🚩 Flag mode** button to toggle — then taps
  place/remove flags instead of opening. (Right-click also flags on desktop.)
- **Power-ups** hide under empty (0-adjacent) areas. Open one to collect it;
  tap it to arm, then your next board tap *uses* it:
  - **Boom 3×3** — peek a 3×3 (mines shown, harmless, no score)
  - **Auto-mark 3×3** — correctly flags every mine in a 3×3 for you (scores)
  - **Flip flag** — flip one existing flag: steal an opponent's, or clear
    your own

## Admin

`/admin` is **local-network only** by construction: requests from
non-private IPs are refused, so remote control requires a VPN into the LAN —
it is not a setting that can be toggled off. First visit sets the admin
password; after that it's password-gated. Admin can resize the board, change
the mine count, and reset the match.

## Layout

```
app.py              server: HTTP + WebSocket, 5s timers, QR, admin, venv bootstrap
game.py             pure game rules — no network, fully unit-tested
static/index.html   the single-page client
tests/test_game.py  plain-assert tests (python tests/test_game.py)
requirements.txt    fastapi + uvicorn + python-multipart + segno
```

The split is the point of the tutorial: **all rules live in `game.py`** and
are tested with plain asserts; `app.py` only adds the network, the
five-second timers, the QR, and admin. Server is authoritative; the client
renders whatever state it's sent.

## Test

```bash
python tests/test_game.py
```
