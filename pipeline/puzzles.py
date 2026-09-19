"""Daily puzzle generators. Every puzzle has exactly one solution.

Three games, each generated here at build time and shipped as JSON with
no solution inside, so the page checks the rules rather than an answer key:

  lanterns — light every cell of a walled grid; lanterns must not see each
             other; a numbered wall says how many lanterns touch it
  camp     — pitch one tent beside every tree; tents never touch, even
             diagonally; the margins say how many tents sit in each line
  nine     — nine letters hiding one nine-letter word; find the words

Generation is seeded, so the same day always gets the same puzzle, and the
uniqueness check is a real solver counting to two, not a hope.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS = 120


# ── Lanterns (Akari) ──────────────────────────────────────────────────────────

def lanterns_solutions(n: int, walls: dict[tuple[int, int], int | None], cap: int = 2) -> int:
    """Count solutions, stopping at `cap`. Cells are decided in row order, so
    an unlit cell can only be lit later by a lantern to its right or below."""
    cells = [(r, c) for r in range(n) for c in range(n) if (r, c) not in walls]
    index = {rc: i for i, rc in enumerate(cells)}
    bulbs: set[tuple[int, int]] = set()
    lit = [[0] * n for _ in range(n)]          # how many lanterns light the cell

    def line(r, c):
        out = []
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            rr, cc = r + dr, c + dc
            while 0 <= rr < n and 0 <= cc < n and (rr, cc) not in walls:
                out.append((rr, cc)); rr += dr; cc += dc
        return out

    lines = {rc: line(*rc) for rc in cells}
    adj_walls = {rc: [(rc[0] + dr, rc[1] + dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))
                      if (rc[0] + dr, rc[1] + dc) in walls and walls[(rc[0] + dr, rc[1] + dc)] is not None]
                 for rc in cells}
    wall_nbrs = {w: [(w[0] + dr, w[1] + dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))
                     if (w[0] + dr, w[1] + dc) in index] for w, v in walls.items() if v is not None}
    count = [0]
    decided = [False] * len(cells)

    def wall_ok(w) -> bool:
        need = walls[w]; have = 0; undecided = 0
        for x in wall_nbrs[w]:
            if x in bulbs: have += 1
            elif not decided[index[x]]: undecided += 1
        return have <= need <= have + undecided

    def can_be_lit_later(i) -> bool:
        r, c = cells[i]
        for x in lines[(r, c)]:
            if index[x] > i and lit[x[0]][x[1]] == 0 and not decided[index[x]]:
                return True
        return False

    def rec(i):
        if count[0] >= cap:
            return
        if i == len(cells):
            count[0] += 1
            return
        r, c = cells[i]
        decided[i] = True
        # option 1: lantern here (only if nothing lights this cell)
        if lit[r][c] == 0:
            bulbs.add((r, c)); lit[r][c] += 1
            for x in lines[(r, c)]: lit[x[0]][x[1]] += 1
            if all(wall_ok(w) for w in adj_walls[(r, c)]):
                rec(i + 1)
            for x in lines[(r, c)]: lit[x[0]][x[1]] -= 1
            lit[r][c] -= 1; bulbs.discard((r, c))
        # option 2: no lantern; the cell must be lit now or later
        if (lit[r][c] > 0 or can_be_lit_later(i)) and all(wall_ok(w) for w in adj_walls[(r, c)]):
            rec(i + 1)
        decided[i] = False

    rec(0)
    return count[0]


def lanterns_puzzle(rnd: random.Random, n: int = 7) -> dict:
    while True:
        walls: dict[tuple[int, int], int | None] = {}
        for r in range(n):
            for c in range(n):
                if rnd.random() < 0.2:
                    walls[(r, c)] = None
        if not 5 <= len(walls) <= 14:
            continue
        # a random full lighting: any unlit cell may take a lantern
        cells = [(r, c) for r in range(n) for c in range(n) if (r, c) not in walls]
        lit = set(); bulbs = set()
        order = cells[:]; rnd.shuffle(order)
        for rc in order:
            if rc in lit:
                continue
            bulbs.add(rc); lit.add(rc)
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                rr, cc = rc[0] + dr, rc[1] + dc
                while 0 <= rr < n and 0 <= cc < n and (rr, cc) not in walls:
                    lit.add((rr, cc)); rr += dr; cc += dc
        # number every wall from that solution, then drop numbers while unique
        for w in walls:
            walls[w] = sum((w[0] + dr, w[1] + dc) in bulbs for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        if lanterns_solutions(n, walls) != 1:
            continue
        keys = list(walls); rnd.shuffle(keys)
        for w in keys:
            v = walls[w]; walls[w] = None
            if lanterns_solutions(n, walls) != 1:
                walls[w] = v
        if len(bulbs) < 6:
            continue
        return {"n": n, "walls": [[r, c, v] for (r, c), v in sorted(walls.items())],
                "_solution": sorted(bulbs)}


# ── Camp (Tents) ──────────────────────────────────────────────────────────────

def camp_solutions(n, trees: set, rows: list[int], cols: list[int], cap: int = 2) -> int:
    cells = [(r, c) for r in range(n) for c in range(n) if (r, c) not in trees
             and any((r + dr, c + dc) in trees for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))]
    tents: list[tuple[int, int]] = []
    rcount = [0] * n; ccount = [0] * n
    count = [0]
    total = sum(rows)

    def touches(rc):
        return any(abs(rc[0] - t[0]) <= 1 and abs(rc[1] - t[1]) <= 1 for t in tents)

    def matchable() -> bool:
        # perfect matching tents -> adjacent trees (simple augmenting paths)
        tree_list = sorted(trees); tidx = {t: i for i, t in enumerate(tree_list)}
        match = [-1] * len(tree_list)
        def adj(t): return [tidx[(t[0] + dr, t[1] + dc)] for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)) if (t[0] + dr, t[1] + dc) in tidx]
        def aug(i, seen):
            for j in adj(tents[i]):
                if j in seen: continue
                seen.add(j)
                if match[j] == -1 or aug(match[j], seen):
                    match[j] = i; return True
            return False
        return all(aug(i, set()) for i in range(len(tents)))

    def rec(i, placed):
        if count[0] >= cap:
            return
        if placed == total:
            if all(rcount[r] == rows[r] for r in range(n)) and all(ccount[c] == cols[c] for c in range(n)) and matchable():
                count[0] += 1
            return
        if i == len(cells) or len(cells) - i < total - placed:
            return
        r, c = cells[i]
        # rows are visited in order: once we pass row r entirely, its count is fixed
        if rcount[r] < rows[r] and ccount[c] < cols[c] and not touches((r, c)):
            tents.append((r, c)); rcount[r] += 1; ccount[c] += 1
            rec(i + 1, placed + 1)
            tents.pop(); rcount[r] -= 1; ccount[c] -= 1
        # skip this cell; prune if the row can no longer be completed
        nxt = cells[i + 1] if i + 1 < len(cells) else None
        if nxt is None or nxt[0] != r:
            remaining_in_row = 0
        else:
            remaining_in_row = sum(1 for x in cells[i + 1:] if x[0] == r)
        if rcount[r] + remaining_in_row >= rows[r]:
            rec(i + 1, placed)

    rec(0, 0)
    return count[0]


def camp_puzzle(rnd: random.Random, n: int = 6) -> dict:
    while True:
        tents: list[tuple[int, int]] = []
        order = [(r, c) for r in range(n) for c in range(n)]; rnd.shuffle(order)
        for rc in order:
            if len(tents) >= n + 1: break
            if any(abs(rc[0] - t[0]) <= 1 and abs(rc[1] - t[1]) <= 1 for t in tents): continue
            tents.append(rc)
        trees: set = set()
        ok = True
        for t in tents:
            opts = [(t[0] + dr, t[1] + dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))]
            opts = [o for o in opts if 0 <= o[0] < n and 0 <= o[1] < n and o not in trees and o not in tents]
            if not opts: ok = False; break
            trees.add(rnd.choice(opts))
        if not ok or len(tents) < n:
            continue
        rows = [sum(1 for t in tents if t[0] == r) for r in range(n)]
        cols = [sum(1 for t in tents if t[1] == c) for c in range(n)]
        if camp_solutions(n, trees, rows, cols) == 1:
            return {"n": n, "trees": sorted(trees), "rows": rows, "cols": cols, "_solution": sorted(tents)}


# ── Nine ──────────────────────────────────────────────────────────────────────

def nine_puzzle(rnd: random.Random, common: list[str], valid: set[str]) -> dict:
    from collections import Counter
    nines = [w for w in common if len(w) == 9 and w in valid and len(set(w)) >= 6]
    while True:
        target = rnd.choice(nines)
        pool = Counter(target)
        words = sorted({w for w in common if 4 <= len(w) <= 9 and w in valid and not (Counter(w) - pool)})
        if len(words) < 25:
            continue
        letters = list(target); rnd.shuffle(letters)
        score = sum(len(w) for w in words) + 20 * sum(1 for w in words if len(w) == 9)
        return {"letters": "".join(letters), "words": words, "max": score,
                "nines": [w for w in words if len(w) == 9]}


# ── build ─────────────────────────────────────────────────────────────────────

def build_puzzles(out_dir: Path, days: int = DAYS) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    common = [w.strip() for w in (ROOT / "data/words/common.txt").read_text().split() if w.strip().isalpha()]
    valid = {w.strip() for w in (ROOT / "data/words/enable1.txt").read_text().split()}

    def strip(p): return {k: v for k, v in p.items() if not k.startswith("_")}
    lant = [lanterns_puzzle(random.Random(1000 + d)) for d in range(days)]
    camp = [camp_puzzle(random.Random(2000 + d)) for d in range(days)]
    nine = [nine_puzzle(random.Random(3000 + d), common, valid) for d in range(days)]
    (out_dir / "lanterns.json").write_text(json.dumps({"puzzles": [strip(p) for p in lant]}))
    (out_dir / "camp.json").write_text(json.dumps({"puzzles": [strip(p) for p in camp]}))
    (out_dir / "nine.json").write_text(json.dumps({"puzzles": nine}))
    # solutions stay out of the site; the test harness reads them from here
    (ROOT / "data" / "puzzle-solutions.json").write_text(json.dumps(
        {"lanterns": [p["_solution"] for p in lant], "camp": [p["_solution"] for p in camp]}))
    return {"lanterns": len(lant), "camp": len(camp), "nine": len(nine)}


if __name__ == "__main__":
    print(build_puzzles(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist/assets/games", int(sys.argv[2]) if len(sys.argv) > 2 else DAYS))
