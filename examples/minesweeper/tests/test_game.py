"""Tests for game.py — plain asserts, no pytest (run: python tests/test_game.py).

Exit 0 = all pass, exit 1 = failure. Mirrors the Nilsson test style so this
project doubles as a tutorial.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from game import Game, BOOM, MARK, FLIP  # noqa: E402

fails: list[str] = []


def ok(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def fresh():
    g = Game(8, 8, 10, powerups=3, seed=42)
    g.add_player("A", "Alice")
    g.add_player("B", "Bob")
    return g


def mines(g):
    return [(r, c) for r in range(g.h) for c in range(g.w) if g.grid[r][c].mine]


def safe0(g):  # a safe, 0-adjacent cell
    for r in range(g.h):
        for c in range(g.w):
            if not g.grid[r][c].mine and g.grid[r][c].adj == 0:
                return r, c


g = fresh()
ok("two players -> playing", g.status == "playing")
ok("mine count exact", len(mines(g)) == 10)

# adjacency recomputed independently
good = True
for r in range(g.h):
    for c in range(g.w):
        if not g.grid[r][c].mine:
            exp = sum(g.grid[nr][nc].mine for nr, nc in g._around(r, c))
            good &= g.grid[r][c].adj == exp
ok("adjacency correct", good)

# powerups only under safe, 0-adjacency cells
pcells = [(r, c) for r in range(g.h) for c in range(g.w) if g.grid[r][c].powerup]
ok("powerups placed", len(pcells) == 3)
ok("powerups on empty safe cells",
   all(not g.grid[r][c].mine and g.grid[r][c].adj == 0 for r, c in pcells))

# pending + cancel (anyone can cancel any pending — self-cancel + veto)
r, c = safe0(g)
g.click("A", r, c)
ok("click creates pending", (r, c) in g.pending and g.pending[(r, c)]["by"] == "A")
g.click("A", r, c)
ok("self-cancel aborts (A clicks own pending)",
   (r, c) not in g.pending and (r, c) not in g.revealed)
g.click("A", r, c)                                  # re-arm pending
ok("pending re-created", (r, c) in g.pending)
g.click("B", r, c)
ok("opponent veto aborts", (r, c) not in g.pending and (r, c) not in g.revealed)

# resolve a safe 0-cell -> floods (reveals more than one)
g.click("A", r, c)
g.resolve_pending(r, c)
ok("safe resolve reveals", (r, c) in g.revealed)
ok("zero-cell floods", len(g.revealed) > 1)

# sudden death on mine
g2 = fresh()
mr, mc = mines(g2)[0]
g2.click("A", mr, mc)
g2.resolve_pending(mr, mc)
ok("mine = sudden death over", g2.status == "over")
ok("opener loses, other wins", g2.winner == "B")

# flag scoring + finish
g3 = fresh()
for (mr, mc) in mines(g3)[:3]:
    g3.flag("A", mr, mc)
ok("correct flags score live", g3.live_score("A") == 3)
g3._finish_by_score()
ok("finish picks higher score", g3.winner == "A" and g3.status == "over")

# MARK power-up: flags every mine in 3x3 for the user, and scores
g4 = fresh()
mr, mc = mines(g4)[0]
g4.players["A"].powerups.append(MARK)
g4.arm("A", MARK)
ok("arm sets armed", g4.players["A"].armed == MARK)
g4.click("A", mr, mc)                       # armed -> uses power-up
ok("MARK flagged the mine for A", g4.flags.get((mr, mc)) == "A")
ok("MARK consumed", MARK not in g4.players["A"].powerups
   and g4.players["A"].armed == 0)

# FLIP power-up: steals an opponent's flag
g5 = fresh()
fr, fc = mines(g5)[0]
g5.flag("B", fr, fc)
g5.players["A"].powerups.append(FLIP)
g5.arm("A", FLIP)
g5.click("A", fr, fc)
ok("FLIP steals opponent flag", g5.flags.get((fr, fc)) == "A")

# BOOM power-up: peeks a 3x3 (mines visible, no sudden death)
g6 = fresh()
br, bc = mines(g6)[0]
g6.players["A"].powerups.append(BOOM)
g6.arm("A", BOOM)
g6.click("A", br, bc)
ok("BOOM peeks, no death", g6.status == "playing" and (br, bc) in g6.peeked)
ok("BOOM view shows mine", g6.view("A")["cells"][br][bc]["s"] == "mine")

# board clear -> ends by score
g7 = fresh()
for rr in range(g7.h):
    for cc in range(g7.w):
        if not g7.grid[rr][cc].mine:
            g7.revealed.add((rr, cc))
g7._check_clear()
ok("all safe revealed ends match", g7.status == "over")


# --- single-player support -------------------------------------------
def solo():
    g = Game(8, 8, 10, powerups=3, seed=42)
    g.add_player("A", "Alice")
    return g


s = solo()
ok("solo: one player → playing", s.status == "playing" and s.is_solo())
ok("solo: starts immediately (not 'waiting')", s.status != "waiting")

# Solo uses the same 5s pending mechanic as multi (no fast-path); the
# player can self-cancel (no opponent is around to do it).
s = solo()
r, c = safe0(s)
s.click("A", r, c)
ok("solo click creates pending (5s mechanic always on)",
   (r, c) in s.pending and s.pending[(r, c)]["by"] == "A")
ok("solo click does not reveal immediately", (r, c) not in s.revealed)
s.click("A", r, c)
ok("solo self-cancel aborts the pending",
   (r, c) not in s.pending and (r, c) not in s.revealed)

# When the pending resolves (server timer fires), behavior matches multi:
# safe → reveal/flood; mine → sudden death (solo loss).
s = solo()
r, c = safe0(s)
s.click("A", r, c)
s.resolve_pending(r, c)
ok("solo resolve reveals on safe", (r, c) in s.revealed)
ok("solo resolve floods (0-cell)", len(s.revealed) > 1)

s = solo()
mr, mc = mines(s)[0]
s.click("A", mr, mc)
ok("solo mine click also pends (no fast-path)",
   (mr, mc) in s.pending)
s.resolve_pending(mr, mc)
ok("solo mine resolve → game over", s.status == "over")
ok("solo mine resolve → no winner (UI shows 'You lose')",
   s.winner is None)

# Solo board clear is a win, not a draw.
s = solo()
for rr in range(s.h):
    for cc in range(s.w):
        if not s.grid[rr][cc].mine:
            s.revealed.add((rr, cc))
s._check_clear()
ok("solo board-clear → winner is the player",
   s.status == "over" and s.winner == "A")

# A 2nd player joining mid-game changes nothing about the cancel rule
# (it's symmetric in both modes); they just have an additional canceller.
s = solo()
s.add_player("B", "Bob")
ok("2nd player joins mid-game: still playing", s.status == "playing")
ok("2nd player joins mid-game: no longer solo", not s.is_solo())


# --- new_match: "🔁 New game" button when the round is over ----------
g = fresh()
ok("new_match no-op mid-game (returns False)", g.new_match() is False)
ok("mid-game state untouched", g.status == "playing")

# End the game by sudden death, then reset.
g = fresh()
mr, mc = mines(g)[0]
g.click("A", mr, mc)
g.resolve_pending(mr, mc)
ok("setup: game over after mine", g.status == "over")
ok("new_match after over (returns True)", g.new_match() is True)
ok("new_match → status back to playing", g.status == "playing")
ok("new_match → winner cleared", g.winner is None)
ok("new_match keeps players seated",
   set(g.players.keys()) == {"A", "B"})
ok("new_match clears flags/revealed/pending",
   len(g.flags) == 0 and len(g.revealed) == 0 and len(g.pending) == 0)
ok("new_match keeps board dimensions",
   g.w == 8 and g.h == 8 and g.n_mines == 10)

# Solo: new_match after a solo loss starts a fresh solo round.
s = solo()
mr, mc = mines(s)[0]
s.click("A", mr, mc)
s.resolve_pending(mr, mc)                           # 5s timer fires (no veto)
ok("solo over before new_match", s.status == "over")
ok("solo new_match works", s.new_match() and s.status == "playing")
ok("solo new_match still solo", s.is_solo())


if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll game tests passed.")
