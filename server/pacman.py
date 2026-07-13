"""A self-playing, arcade-faithful Pac-Man for the 32x32 LED wall.

Pure game logic + a render() that returns {(x, y): (r, g, b)} for the lit cells
of the current frame (black elsewhere). The daemon diffs frames and pushes only
changed pixels via Graffiti, so the panel never full-refreshes (no flashing).

Fidelity to the 1980 Namco original (per the Pac-Man Dossier, cross-checked):
  * the classic 28x31 maze, centered on the panel (tile col,row -> x+2,y), with
    the horizontal tunnel on row 14 that wraps left<->right;
  * the four ghosts with their REAL target-tile algorithms:
      Blinky (red)   = Pac-Man's tile (+ Cruise Elroy speedup as dots deplete),
      Pinky (pink)   = 4 tiles ahead of Pac-Man (incl. the up-overflow bug),
      Inky  (cyan)   = double the vector from Blinky through 2-ahead of Pac-Man,
      Clyde (orange) = Pac-Man if >8 tiles away, else his scatter corner;
  * scatter/chase schedule 7/20/7/20/5/20/5 s then chase forever, with a forced
    reverse on every mode flip;
  * intersection rule: the legal non-reversing move minimizing straight-line
    distance to the target, tie-break up > left > down > right, with the lower
    "no upward turn" tiles honored;
  * energizers -> frightened ghosts (reverse, wander, 50% speed, blue then
    flashing white), eaten for 200/400/800/1600, eyes race home and regenerate;
  * dot-counter house release (Pinky 0, Inky 30, Clyde 60) with bobbing.

Pac-Man is AI-driven (it's an ambient display, not a controller): he eats the
nearest pellet, grabs energizers and hunts frightened ghosts, and flees when a
live ghost closes in.

Note vs. the Dossier: the upper no-up tiles (12,11)/(15,11) are omitted — in this
maze reproduction they sit on the only shafts ghosts use to exit the pen, so
enforcing them would trap the ghosts. The lower pair is kept.
"""

from __future__ import annotations

import math
import random
from collections import deque

# ---- maze --------------------------------------------------------------------
# # wall  . pellet  o energizer  (space) empty path  - ghost-house door
MAZE = [
    "############################",  # 0
    "#............##............#",  # 1
    "#.####.#####.##.#####.####.#",  # 2
    "#o####.#####.##.#####.####o#",  # 3   energizers col 1 & 26
    "#.####.#####.##.#####.####.#",  # 4
    "#..........................#",  # 5
    "#.####.##.########.##.####.#",  # 6
    "#.####.##.########.##.####.#",  # 7
    "#......##....##....##......#",  # 8
    "######.##### ## #####.######",  # 9
    "     #.##### ## #####.#     ",  # 10
    "     #.##          ##.#     ",  # 11  Blinky spawns (13,11)
    "     #.## ###--### ##.#     ",  # 12  door at (13,12)/(14,12)
    "######.## #      # ##.######",  # 13
    "      .   #      #   .      ",  # 14  TUNNEL row (col 0 <-> col 27)
    "######.## #      # ##.######",  # 15
    "     #.## ######## ##.#     ",  # 16
    "     #.##          ##.#     ",  # 17
    "     #.## ######## ##.#     ",  # 18
    "######.## ######## ##.######",  # 19
    "#............##............#",  # 20
    "#.####.#####.##.#####.####.#",  # 21
    "#.####.#####.##.#####.####.#",  # 22
    "#o..##.......  .......##..o#",  # 23  energizers col 1 & 26; Pac start col 13/14
    "###.##.##.########.##.##.###",  # 24
    "###.##.##.########.##.##.###",  # 25
    "#......##....##....##......#",  # 26
    "#.##########.##.##########.#",  # 27
    "#.##########.##.##########.#",  # 28
    "#..........................#",  # 29
    "############################",  # 30
]

MW, MH = 28, 31          # maze tile dimensions
OX, OY = 2, 0            # panel offset: tile (c,r) -> pixel (c+OX, r+OY)
TUNNEL_ROWS = {14}       # rows whose col 0 <-> col 27 wrap

# key tiles (col, row)
PAC_START = (13, 23)
DOOR = (13, 12)
HOUSE_CENTER = (13, 14)
GHOST_START = {"blinky": (13, 11), "pinky": (13, 14), "inky": (12, 14), "clyde": (15, 14)}
SCATTER = {"blinky": (25, 0), "pinky": (2, 0), "inky": (27, 30), "clyde": (0, 30)}
RELEASE_DOTS = {"blinky": 0, "pinky": 0, "inky": 30, "clyde": 60}
NO_UP = {(12, 23), (15, 23)}   # lower no-up pair (see module note)

# ---- palette -----------------------------------------------------------------
WALL = (36, 44, 240)      # iconic Pac-Man blue
DOOR_C = (240, 170, 210)   # pink house door
DOT = (104, 86, 70)        # dim pellets so the blue maze reads as structure
ENERGIZER = (255, 210, 180)
PAC = (255, 236, 0)
FRIGHT = (36, 40, 220)
FRIGHT_FLASH = (240, 240, 255)
EYES = (190, 214, 255)
GHOST_COLOR = {"blinky": (255, 40, 30), "pinky": (255, 170, 225),
               "inky": (60, 230, 235), "clyde": (255, 176, 70)}

UP, LEFT, DOWN, RIGHT = (0, -1), (-1, 0), (0, 1), (1, 0)
DIR_ORDER = [UP, LEFT, DOWN, RIGHT]        # tie-break priority

SCHEDULE = [("scatter", 7), ("chase", 20), ("scatter", 7), ("chase", 20),
            ("scatter", 5), ("chase", 20), ("scatter", 5), ("chase", None)]
FPS = 11                  # frames ~= one game-second (~0.09s/frame)
FRIGHT_FRAMES = 6 * FPS
FRIGHT_FLASH_AT = 2 * FPS


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _rev(d):
    return (-d[0], -d[1])


class Ghost:
    def __init__(self, name, tile):
        self.name = name
        self.color = GHOST_COLOR[name]
        self.home = tile
        self.tile = tile
        self.dir = LEFT
        self.state = "out" if name == "blinky" else "house"  # house|leaving|out|fright|eyes
        self.move_acc = 0.0
        self.bob = 0


class PacMan:
    def __init__(self, n: int, rng: random.Random | None = None):
        self.n = n
        self.rng = rng or random.Random()
        self._parse_maze()
        self.reset_all()

    # ---------- maze setup ----------
    def _parse_maze(self):
        assert len(MAZE) == MH, f"maze has {len(MAZE)} rows, need {MH}"
        for i, row in enumerate(MAZE):
            assert len(row) == MW, f"row {i} is {len(row)} wide, need {MW}"
        self.walls, self.doors, self.base_dots, self.base_energ = set(), set(), set(), set()
        for r in range(MH):
            for c in range(MW):
                ch = MAZE[r][c]
                if ch == "#":
                    self.walls.add((c, r))
                elif ch == "-":
                    self.doors.add((c, r))
                elif ch == ".":
                    self.base_dots.add((c, r))
                elif ch == "o":
                    self.base_energ.add((c, r))

    def neighbor(self, tile, d):
        """Next tile in direction d, applying tunnel wrap; None if off-maze."""
        c, r = tile[0] + d[0], tile[1] + d[1]
        if c < 0 or c >= MW:
            if r in TUNNEL_ROWS:
                c %= MW
            else:
                return None
        if r < 0 or r >= MH:
            return None
        return (c, r)

    def passable(self, tile, *, ghost=False, through_door=False):
        if tile is None or tile in self.walls:
            return False
        if tile in self.doors:
            return ghost and through_door
        return True

    # ---------- lifecycle ----------
    def reset_all(self):
        self.score = 0
        self.dots = set(self.base_dots)
        self.energ = set(self.base_energ)
        self.dots_eaten = 0
        self.lives = 3
        self.dead = False
        self.frame = 0
        self.blink = 0
        self._reset_actors()

    def _reset_actors(self):
        self.pac = PAC_START
        self.pac_dir = LEFT
        self.pac_acc = 0.0
        self.ghosts = {name: Ghost(name, GHOST_START[name])
                       for name in ("blinky", "pinky", "inky", "clyde")}
        self.mode_i = 0
        self.mode = SCHEDULE[0][0]
        self.mode_timer = SCHEDULE[0][1] * FPS
        self.fright = 0
        self.fright_chain = 0
        self.reverse_flag = False

    # ---------- mode scheduling ----------
    def _tick_mode(self):
        if self.fright > 0:                    # frightened pauses the scatter/chase clock
            self.fright -= 1
            if self.fright == 0:
                for g in self.ghosts.values():
                    if g.state == "fright":
                        g.state = "out"
            return
        if self.mode_timer is None:
            return
        self.mode_timer -= 1
        if self.mode_timer <= 0:
            self.mode_i += 1
            if self.mode_i < len(SCHEDULE):
                self.mode, secs = SCHEDULE[self.mode_i]
                self.mode_timer = None if secs is None else secs * FPS
                self.reverse_flag = True       # forced reverse on mode flip

    # ---------- ghost targeting ----------
    def _target_chase(self, g):
        pac, pd = self.pac, self.pac_dir
        if g.name == "blinky":
            return pac
        if g.name == "pinky":
            if pd == UP:                       # up-overflow bug: also 4 left
                return (pac[0] - 4, pac[1] - 4)
            return (pac[0] + 4 * pd[0], pac[1] + 4 * pd[1])
        if g.name == "inky":
            pivot = (pac[0] - 2, pac[1] - 2) if pd == UP else \
                    (pac[0] + 2 * pd[0], pac[1] + 2 * pd[1])
            b = self.ghosts["blinky"].tile
            return (pivot[0] * 2 - b[0], pivot[1] * 2 - b[1])
        if g.name == "clyde":
            return pac if math.dist(g.tile, pac) > 8 else SCATTER["clyde"]
        return pac

    def _ghost_target(self, g):
        if g.state == "eyes":
            return DOOR
        return SCATTER[g.name] if self.mode == "scatter" else self._target_chase(g)

    def _ghost_speed(self, g):
        if g.state == "eyes":
            return 1.6
        if g.state == "fright":
            return 0.5
        if g.tile[1] == 14 and (g.tile[0] <= 5 or g.tile[0] >= 22):   # tunnel
            return 0.4
        if g.name == "blinky":                 # Cruise Elroy
            left = len(self.dots) + len(self.energ)
            if left <= 10:
                return 0.85
            if left <= 20:
                return 0.80
        return 0.75

    def _legal_dirs(self, g, allow_reverse=False):
        out = []
        for d in DIR_ORDER:
            if not allow_reverse and d == _rev(g.dir):
                continue
            nxt = self.neighbor(g.tile, d)
            if nxt is None:
                continue
            through = g.state == "eyes" or g.tile in self.doors or nxt in self.doors
            if not self.passable(nxt, ghost=True, through_door=through):
                continue
            if d == UP and g.tile in NO_UP and g.state not in ("eyes", "fright"):
                continue
            out.append((d, nxt))
        return out

    def _choose_dir(self, g):
        options = self._legal_dirs(g) or self._legal_dirs(g, allow_reverse=True)
        if not options:
            return g.dir
        if g.state == "fright":
            return self.rng.choice(options)[0]
        target = self._ghost_target(g)
        return min(options, key=lambda o: (math.dist(o[1], target),
                                           DIR_ORDER.index(o[0])))[0]

    # ---------- ghost movement ----------
    def _move_ghost(self, g):
        if g.state == "house":
            g.bob = (g.bob + 1) % 4
            if self.dots_eaten >= RELEASE_DOTS[g.name]:
                g.state = "leaving"
            return
        if g.state == "leaving":
            tc, tr = g.tile
            if tc != DOOR[0]:
                g.tile = (tc + (1 if tc < DOOR[0] else -1), tr)
            elif tr > DOOR[1] - 1:
                g.tile = (tc, tr - 1)
            if g.tile == (DOOR[0], DOOR[1] - 1):
                g.state, g.dir, g.move_acc = "out", LEFT, 0.0
            return

        if self.reverse_flag and g.state in ("out", "fright"):
            g.dir = _rev(g.dir)                # one-time forced reverse
        g.move_acc += self._ghost_speed(g)
        while g.move_acc >= 1.0:
            g.move_acc -= 1.0
            g.dir = self._choose_dir(g)
            nxt = self.neighbor(g.tile, g.dir)
            if nxt is None:
                break
            g.tile = nxt
            if g.state == "eyes" and g.tile in (DOOR, (DOOR[0], DOOR[1] - 1), HOUSE_CENTER):
                g.state, g.tile, g.dir, g.move_acc = "out", (DOOR[0], DOOR[1] - 1), LEFT, 0.0
                break

    # ---------- Pac-Man AI ----------
    def _bfs(self, sources):
        dist = {s: 0 for s in (sources if isinstance(sources, (list, set)) else [sources])
                if self.passable(s)}
        q = deque(dist)
        while q:
            t = q.popleft()
            for d in DIR_ORDER:
                nxt = self.neighbor(t, d)
                if nxt is None or nxt in dist or not self.passable(nxt):
                    continue
                dist[nxt] = dist[t] + 1
                q.append(nxt)
        return dist

    def _nearest(self, dist, targets):
        best, bd = None, 1e9
        for t in targets:
            if dist.get(t, 1e9) < bd:
                best, bd = t, dist[t]
        return best, bd

    def _pac_target(self, dist):
        live = [g for g in self.ghosts.values() if g.state == "out"]
        fright = [g for g in self.ghosts.values() if g.state == "fright"]
        near = min((dist.get(g.tile, 99) for g in live), default=99)
        if fright:                             # hunt scared ghosts
            tgt, _ = self._nearest(dist, [g.tile for g in fright])
            if tgt:
                return tgt, False
        if near <= 4:                          # danger: grab a nearby energizer, else flee
            tgt, ed = self._nearest(dist, self.energ)
            if tgt and ed <= 6:
                return tgt, False
            return None, True
        tgt, _ = self._nearest(dist, self.dots | self.energ)
        return tgt, False

    def _pac_choose(self):
        dist = self._bfs(self.pac)
        target, flee = self._pac_target(dist)
        options = [(d, self.neighbor(self.pac, d)) for d in DIR_ORDER]
        options = [(d, t) for d, t in options if self.passable(t)]
        if not options:
            return self.pac_dir, self.pac
        if flee or target is None:
            gd = self._bfs([g.tile for g in self.ghosts.values() if g.state == "out"])
            d, nxt = min(options, key=lambda o: (-gd.get(o[1], 99), o[0] == _rev(self.pac_dir)))
            return d, nxt
        tdist = self._bfs(target)
        d, nxt = min(options, key=lambda o: (tdist.get(o[1], 1e9), o[0] == _rev(self.pac_dir)))
        return d, nxt

    def _move_pac(self):
        self.pac_acc += 0.8                    # ~80% base speed
        while self.pac_acc >= 1.0:
            self.pac_acc -= 1.0
            self.pac_dir, self.pac = self._pac_choose()
            self._eat()

    def _eat(self):
        if self.pac in self.dots:
            self.dots.discard(self.pac)
            self.dots_eaten += 1
            self.score += 10
        elif self.pac in self.energ:
            self.energ.discard(self.pac)
            self.dots_eaten += 1
            self.score += 50
            self.fright = FRIGHT_FRAMES
            self.fright_chain = 0
            for g in self.ghosts.values():
                if g.state == "out":
                    g.state, g.dir, g.move_acc = "fright", _rev(g.dir), 0.0

    # ---------- collisions ----------
    def _collide(self):
        for g in self.ghosts.values():
            if g.tile != self.pac:
                continue
            if g.state == "fright":
                self.fright_chain = min(self.fright_chain + 1, 4)
                self.score += 100 * (2 ** self.fright_chain)   # 200/400/800/1600
                g.state = "eyes"
            elif g.state == "out":
                self.lives -= 1
                self.dead = self.lives <= 0
                if not self.dead:
                    self._reset_actors()
                return

    # ---------- one tick ----------
    def step(self):
        self.frame += 1
        self.blink = (self.blink + 1) % (FPS or 1)
        self._tick_mode()
        self._move_pac()
        self._collide()
        if self.dead:
            return
        for g in self.ghosts.values():
            self._move_ghost(g)
        self.reverse_flag = False
        self._collide()
        if not self.dots and not self.energ:   # board cleared
            self.dead = True

    # ---------- render ----------
    def _px(self, tile):
        return (tile[0] + OX, tile[1] + OY)

    def render(self) -> dict:
        cells = {}
        for t in self.walls:
            cells[self._px(t)] = WALL
        for t in self.doors:
            cells[self._px(t)] = DOOR_C
        for t in self.dots:
            cells[self._px(t)] = DOT
        if self.blink < FPS // 2:              # energizers blink
            for t in self.energ:
                cells[self._px(t)] = ENERGIZER
        flashing = 0 < self.fright <= FRIGHT_FLASH_AT and self.blink % 2 == 0
        for g in self.ghosts.values():
            if g.state == "eyes":
                col = EYES
            elif g.state == "fright":
                col = FRIGHT_FLASH if flashing else FRIGHT
            else:
                col = g.color
            cells[self._px(g.tile)] = col
        cells[self._px(self.pac)] = PAC
        return {(x, y): c for (x, y), c in cells.items() if 0 <= x < self.n and 0 <= y < self.n}
