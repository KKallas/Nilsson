"""game.py — pure, testable multiplayer-minesweeper rules. No network, no async.

Server-authoritative: app.py owns the 5-second timers and sockets and calls
into this module; all game truth lives here so it can be unit-tested with
plain asserts (see tests/test_game.py).

Rules (locked):
- 1v1 on a shared board. Flags are instant, owned, and final — they cannot
  be challenged. Your score = flags you placed that sit on a mine.
- Opening a cell is a 5s *pending* action. The OTHER player may click that
  pending cell to **veto** it (abort, cell stays closed, no score). You
  cannot veto your own. (Timing is handled by app.py.)
- Sudden death: if a pending open resolves onto a mine, the match ends
  immediately and the other player wins. If instead every safe cell is
  opened (or every mine flagged), the match ends and the higher correct-flag
  count wins (equal → draw).
- Power-ups hide under empty (0-adjacent) cells. Opening such a cell grants
  it. Arm it, then your next board click *uses* it instead of opening:
    1 BOOM   — peek a 3x3 (mines shown, harmless, no score)
    2 MARK   — correctly flag every mine in a 3x3 for you (scores)
    3 FLIP   — flip one existing flag: steal an opponent's / clear your own
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

BOOM, MARK, FLIP = 1, 2, 3
POWERUP_NAMES = {BOOM: "Boom 3x3", MARK: "Auto-mark 3x3", FLIP: "Flip flag"}
PENDING_SECONDS = 5.0


@dataclass
class Cell:
    mine: bool = False
    adj: int = 0
    powerup: int = 0  # 0 = none, else BOOM/MARK/FLIP


@dataclass
class Player:
    pid: str
    name: str
    score: int = 0
    powerups: list[int] = field(default_factory=list)
    armed: int = 0  # 0 = none armed


class Game:
    def __init__(self, w: int = 16, h: int = 16, mines: int = 40,
                 powerups: int = 6, seed: int | None = None) -> None:
        self.reset(w, h, mines, powerups, seed)

    # ---- lifecycle ---------------------------------------------------
    def reset(self, w: int, h: int, mines: int, powerups: int = 6,
              seed: int | None = None) -> None:
        rnd = random.Random(seed)
        self.w, self.h, self.n_mines = w, h, mines
        self.grid = [[Cell() for _ in range(w)] for _ in range(h)]
        self.players: dict[str, Player] = {}
        self.revealed: set[tuple[int, int]] = set()
        self.peeked: set[tuple[int, int]] = set()      # BOOM reveals
        self.flags: dict[tuple[int, int], str] = {}     # (r,c) -> pid
        self.pending: dict[tuple[int, int], dict] = {}  # (r,c)->{by,deadline}
        self.status = "waiting"                         # waiting|playing|over
        self.winner: str | None = None                  # pid | "draw" | None

        cells = [(r, c) for r in range(h) for c in range(w)]
        for r, c in rnd.sample(cells, mines):
            self.grid[r][c].mine = True
        for r in range(h):
            for c in range(w):
                if not self.grid[r][c].mine:
                    self.grid[r][c].adj = sum(
                        self.grid[nr][nc].mine for nr, nc in self._around(r, c)
                    )
        # power-ups go under empty (0-adjacent) non-mine cells
        empty = [(r, c) for r in range(h) for c in range(w)
                 if not self.grid[r][c].mine and self.grid[r][c].adj == 0]
        rnd.shuffle(empty)
        for i, (r, c) in enumerate(empty[:powerups]):
            self.grid[r][c].powerup = (BOOM, MARK, FLIP)[i % 3]

    def add_player(self, pid: str, name: str) -> bool:
        """Seat a player (max 2). Match starts when the 2nd joins."""
        if pid in self.players:
            return True
        if len(self.players) >= 2:
            return False
        self.players[pid] = Player(pid, name)
        if len(self.players) == 2:
            self.status = "playing"
        return True

    def _other(self, pid: str) -> str | None:
        for q in self.players:
            if q != pid:
                return q
        return None

    def _around(self, r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.h and 0 <= nc < self.w:
                        yield nr, nc

    # ---- input -------------------------------------------------------
    def click(self, pid: str, r: int, c: int) -> None:
        """A left-click. Arms power-up use, vetoes, or starts a pending open."""
        if self.status != "playing" or pid not in self.players:
            return
        p = self.players[pid]
        if p.armed:
            self._use_powerup(p, r, c)
            return
        key = (r, c)
        if key in self.pending:
            # clicking a pending cell = veto, but only the opponent's
            if self.pending[key]["by"] != pid:
                del self.pending[key]            # abort, no score
            return
        if key in self.revealed or key in self.flags:
            return
        self.pending[key] = {"by": pid, "deadline": time.time() + PENDING_SECONDS}

    def resolve_pending(self, r: int, c: int) -> None:
        """Called by app.py when 5s elapse without a veto."""
        key = (r, c)
        info = self.pending.pop(key, None)
        if info is None or self.status != "playing":
            return
        if self.grid[r][c].mine:                  # sudden death
            self.status, self.winner = "over", self._other(info["by"])
            return
        self._open(info["by"], r, c)
        self._check_clear()

    def flag(self, pid: str, r: int, c: int) -> None:
        """Instant, final. Toggles your own flag off; never touches others'."""
        if self.status != "playing" or pid not in self.players:
            return
        key = (r, c)
        if key in self.revealed or key in self.pending:
            return
        owner = self.flags.get(key)
        if owner is None:
            self.flags[key] = pid
        elif owner == pid:
            del self.flags[key]                   # un-flag your own mistake

    def arm(self, pid: str, ptype: int) -> None:
        p = self.players.get(pid)
        if p and self.status == "playing" and ptype in p.powerups:
            p.armed = 0 if p.armed == ptype else ptype

    # ---- internals ---------------------------------------------------
    def _open(self, pid: str, r: int, c: int) -> None:
        """Flood-fill reveal from a safe cell; collect any power-ups."""
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if (cr, cc) in self.revealed or self.grid[cr][cc].mine:
                continue
            self.revealed.add((cr, cc))
            self.flags.pop((cr, cc), None)
            pu = self.grid[cr][cc].powerup
            if pu:
                self.players[pid].powerups.append(pu)
                self.grid[cr][cc].powerup = 0
            if self.grid[cr][cc].adj == 0:
                for nr, nc in self._around(cr, cc):
                    if (nr, nc) not in self.revealed:
                        stack.append((nr, nc))

    def _use_powerup(self, p: Player, r: int, c: int) -> None:
        kind, p.armed = p.armed, 0
        if kind not in p.powerups:
            return
        p.powerups.remove(kind)
        if kind == BOOM:
            for nr, nc in list(self._around(r, c)) + [(r, c)]:
                self.peeked.add((nr, nc))
        elif kind == MARK:
            for nr, nc in list(self._around(r, c)) + [(r, c)]:
                if (self.grid[nr][nc].mine and (nr, nc) not in self.revealed
                        and (nr, nc) not in self.flags):
                    self.flags[(nr, nc)] = p.pid
        elif kind == FLIP:
            owner = self.flags.get((r, c))
            if owner and owner != p.pid:
                self.flags[(r, c)] = p.pid        # steal
            elif owner == p.pid:
                del self.flags[(r, c)]            # clear

    def _check_clear(self) -> None:
        safe = self.w * self.h - self.n_mines
        if len(self.revealed) >= safe:
            self._finish_by_score()

    def _finish_by_score(self) -> None:
        for q, pl in self.players.items():
            pl.score = sum(1 for (fr, fc), o in self.flags.items()
                            if o == q and self.grid[fr][fc].mine)
        self.status = "over"
        ps = list(self.players.values())
        if len(ps) == 2 and ps[0].score != ps[1].score:
            self.winner = max(ps, key=lambda x: x.score).pid
        else:
            self.winner = "draw"

    def live_score(self, pid: str) -> int:
        return sum(1 for (fr, fc), o in self.flags.items()
                   if o == pid and self.grid[fr][fc].mine)

    # ---- view --------------------------------------------------------
    def view(self, viewer: str) -> dict:
        """Board as `viewer` may see it. app.py adds pending countdowns."""
        over = self.status == "over"
        cells = []
        for r in range(self.h):
            row = []
            for c in range(self.w):
                k = (r, c)
                cell: dict = {}
                if k in self.revealed:
                    cell = {"s": "open", "n": self.grid[r][c].adj}
                elif k in self.flags:
                    cell = {"s": "flag", "own": self.flags[k] == viewer}
                elif k in self.pending:
                    cell = {"s": "pending",
                            "mine_by_me": self.pending[k]["by"] == viewer}
                elif over or k in self.peeked:
                    cell = {"s": "mine" if self.grid[r][c].mine else "hidden"}
                else:
                    cell = {"s": "hidden"}
                if (over or k in self.peeked) and self.grid[r][c].mine \
                        and cell["s"] != "flag":
                    cell["s"] = "mine"
                row.append(cell)
            cells.append(row)
        me = self.players.get(viewer)
        return {
            "w": self.w, "h": self.h, "status": self.status,
            "winner": self.winner, "cells": cells,
            "you": viewer,
            "players": [
                {"pid": q, "name": pl.name, "score": self.live_score(q),
                 "is_you": q == viewer}
                for q, pl in self.players.items()
            ],
            "powerups": (me.powerups if me else []),
            "armed": (me.armed if me else 0),
            "powerup_names": POWERUP_NAMES,
        }
