#!/usr/bin/env python3
"""
mazegen.py - Standalone maze generation module (reusable).

This module provides the MazeGenerator class which can generate perfect
or imperfect mazes with a given seed, entry/exit, and optional "42" pattern.

Usage example:
    from mazegen import MazeGenerator

    gen = MazeGenerator(width=20, height=15,
                        entry=(0, 0), exit_=(19, 14),
                        perfect=True, seed=42)
    print(gen.display_ascii())
    print(gen.path)          # ['S', 'E', ...]
    print(gen.forty_two_cells)

The grid is stored as a list of lists of integers (0-15) where each bit
encodes a closed wall: 1=N, 2=E, 4=S, 8=W.
"""

import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Direction vectors: (dx, dy, wall_bit, letter)
DIRS: List[Tuple[int, int, int, str]] = [
    (0, -1, 1, "N"),  # North
    (1, 0, 2, "E"),   # East
    (0, 1, 4, "S"),   # South
    (-1, 0, 8, "W"),  # West
]

# Opposite wall bit for each direction letter
OPPOSITE: Dict[str, int] = {"N": 4, "S": 1, "E": 8, "W": 2}

# "42" pixel patterns (5 rows × 3 cols, 1 = filled cell)
_P4: List[List[int]] = [
    [1, 0, 0],
    [1, 0, 0],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]
_P2: List[List[int]] = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]

_PAT_H: int = 5
_PAT_W: int = 3
_GAP: int = 1
_TOT_W: int = _PAT_W + _GAP + _PAT_W  # = 7
_MIN_W: int = _TOT_W + 2  # need 1-cell margin on each side
_MIN_H: int = _PAT_H + 2


class MazeGenerator:
    """
    Generate a perfect or imperfect maze with entry/exit and optional "42".

    Attributes:
        width (int): Number of columns.
        height (int): Number of rows.
        entry (Tuple[int, int]): (x, y) of the entry cell.
        exit (Tuple[int, int]): (x, y) of the exit cell.
        perfect (bool): True if maze has a unique path between any two cells.
        seed (Optional[int]): RNG seed for reproducibility.
        grid (List[List[int]]): 2D list of wall bitmasks.
        path (List[str]): BFS solution as list of direction letters.
        forty_two_cells (Set[Tuple[int, int]]):
            Coordinates of the "42" pattern.
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: Tuple[int, int],
        exit_: Tuple[int, int],
        perfect: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        """
        Validate parameters and generate the maze immediately.

        Raises:
            ValueError: Invalid dimensions, out-of-bounds, same entry/exit,
                        or overlap with "42".
            RuntimeError: If generation fails to produce a connected maze.
        """
        self._validate(width, height, entry, exit_)
        self.width: int = width
        self.height: int = height
        self.entry: Tuple[int, int] = entry
        self.exit: Tuple[int, int] = exit_
        self.perfect: bool = perfect
        self.seed: Optional[int] = seed
        self._rng: random.Random = random.Random(seed)

        self.grid: List[List[int]] = []
        self.path: List[str] = []
        self.forty_two_cells: Set[Tuple[int, int]] = set()

        self.generate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """
        (Re-)generate the maze from scratch, updating grid, path, and 42 cells.

        This method resets the RNG with the stored seed, so repeated calls
        with the same seed produce identical mazes.
        """
        self._rng = random.Random(self.seed)

        # Start with all walls closed
        self.grid = [[15] * self.width for _ in range(self.height)]

        # Place the "42" pattern (reserve cells, fail if overlap)
        self._place_forty_two()

        # Carve passages using iterative DFS (avoids 42 cells)
        self._carve_dfs()

        # If not perfect, introduce extra passages (loops)
        if not self.perfect:
            self._add_loops()

        # Ensure no 3x3 open area exists
        self._fix_wide_open()

        # Synchronise wall symmetry
        self._sync_walls()

        # Compute the shortest path from entry to exit
        self.path = self._bfs_path()

        if not self.path and self.entry != self.exit:
            raise RuntimeError(
                "No path from entry to exit - generation failed. "
                "Try a different seed or larger dimensions."
            )

    def export_to_file(self, filename: str) -> None:
        """
        Write the maze to a file in the required hexadecimal format.

        The file contains:
            - One row per line, each cell as an uppercase hex digit.
            - A blank line.
            - Entry coordinates: "x,y".
            - Exit coordinates: "x,y".
            - Solution path as a string of direction letters.

        Args:
            filename: Path to the output file.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(filename, "w") as f:
            for row in self.grid:
                f.write("".join(f"{cell:X}" for cell in row) + "\n")
            f.write("\n")
            f.write(f"{self.entry[0]},{self.entry[1]}\n")
            f.write(f"{self.exit[0]},{self.exit[1]}\n")
            f.write(self.get_solution_letters() + "\n")

    def get_solution_letters(self) -> str:
        """Return the path as a single string of direction letters."""
        return "".join(self.path)

    def display_ascii(self, show_path: bool = False) -> str:
        """
        Return a plain ASCII representation of the maze (no colors).

        Symbols:
            S - entry
            E - exit
            # - "42" cell
            . - solution path (if show_path is True)
            (space) - open cell

        Args:
            show_path: If True, overlay the solution path.

        Returns:
            Multi-line string.
        """
        if not self.grid:
            return "Maze not generated yet."

        W, H = self.width, self.height
        path_cells = set()
        if show_path and self.path:
            cx, cy = self.entry
            path_cells.add((cx, cy))
            dir_map = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
            for letter in self.path:
                dx, dy = dir_map[letter]
                cx += dx
                cy += dy
                path_cells.add((cx, cy))

        lines = []
        for gy in range(2 * H + 1):
            if gy % 2 == 0:
                # Horizontal wall row
                cy = gy // 2
                row = "+"
                for gx in range(W):
                    if cy == 0:
                        has_wall = bool(self.grid[0][gx] & 1)
                    elif cy == H:
                        has_wall = bool(self.grid[H - 1][gx] & 4)
                    else:
                        has_wall = bool(self.grid[cy][gx] & 1)
                    row += "---+" if has_wall else "   +"
            else:
                # Cell row
                cy = gy // 2
                row = ""
                for gx in range(W):
                    row += "|" if (self.grid[cy][gx] & 8) else " "
                    if (gx, cy) == self.entry:
                        row += " S "
                    elif (gx, cy) == self.exit:
                        row += " E "
                    elif (gx, cy) in self.forty_two_cells:
                        row += "###"
                    elif show_path and (gx, cy) in path_cells:
                        row += " . "
                    else:
                        row += "   "
                row += "|" if (self.grid[cy][W - 1] & 2) else " "
            lines.append(row)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(
        width: int,
        height: int,
        entry: Tuple[int, int],
        exit_: Tuple[int, int],
    ) -> None:
        """Raise ValueError if any parameter is invalid."""
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("WIDTH and HEIGHT must be integers.")
        if width < 2 or height < 2:
            raise ValueError(
                f"Maze must be at least 3x3, got {width}x{height}."
            )
        ex, ey = entry
        xx, xy = exit_
        if not (0 <= ex < width and 0 <= ey < height):
            raise ValueError(
                f"ENTRY {entry} outside bounds (0..{width-1},0..{height-1})."
            )
        if not (0 <= xx < width and 0 <= xy < height):
            raise ValueError(f"EXIT {exit_} outside bounds.")
        if entry == exit_:
            raise ValueError(f"ENTRY and EXIT must differ, both are {entry}.")
        # NO BORDER REQUIREMENT - entry/exit can be anywhere inside!

    # ------------------------------------------------------------------
    # "42" placement
    # ------------------------------------------------------------------

    def _place_forty_two(self) -> None:
        """Reserve cells for the "42" pattern, centred in the maze.

        If the maze is too small, print a warning and skip.
        """
        self.forty_two_cells = set()
        if self.width < _MIN_W or self.height < _MIN_H:
            print(
                f"Warning: {self.width}x{self.height} too small for '42' "
                f"(need {_MIN_W}x{_MIN_H}) - skipping."
            )
            return

        sx = (self.width - _TOT_W) // 2
        sy = (self.height - _PAT_H) // 2

        cells: Set[Tuple[int, int]] = set()
        for row in range(_PAT_H):
            for col in range(_PAT_W):
                if _P4[row][col]:
                    cells.add((sx + col, sy + row))
            for col in range(_PAT_W):
                if _P2[row][col]:
                    cells.add((sx + _PAT_W + _GAP + col, sy + row))

        # Entry/exit must not overlap the pattern
        if self.entry in cells:
            raise ValueError(f"ENTRY {self.entry} overlaps the '42' pattern.")
        if self.exit in cells:
            raise ValueError(f"EXIT {self.exit} overlaps the '42' pattern.")

        self.forty_two_cells = cells

    # ------------------------------------------------------------------
    # Maze carving (iterative DFS)
    # ------------------------------------------------------------------

    def _carve_dfs(self) -> None:
        """Carve passages using recursive backtracker, avoiding 42 cells."""
        visited = [[False] * self.width for _ in range(self.height)]
        # Mark 42 cells as visited so we never enter them
        for cx, cy in self.forty_two_cells:
            visited[cy][cx] = True

        stack = [self.entry]
        visited[self.entry[1]][self.entry[0]] = True

        while stack:
            cx, cy = stack[-1]
            # Gather unvisited neighbours
            neighbours = []
            for dx, dy, bit, letter in DIRS:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if not visited[ny][nx]:
                        neighbours.append((nx, ny, bit, letter))

            if neighbours:
                nx, ny, bit, letter = self._rng.choice(neighbours)
                # Remove wall between current and chosen neighbour
                self.grid[cy][cx] &= ~bit
                self.grid[ny][nx] &= ~OPPOSITE[letter]
                visited[ny][nx] = True
                stack.append((nx, ny))
            else:
                stack.pop()

        # Ensure all non-42 cells are reachable (should not happen, but safe)
        self._reconnect_isolated(visited)

    def _reconnect_isolated(self, visited: List[List[bool]]) -> None:
        """Force-connect any unvisited cell to the main network."""
        for y in range(self.height):
            for x in range(self.width):
                if visited[y][x] or (x, y) in self.forty_two_cells:
                    continue
                # Try to open a wall to any visited neighbour
                for dx, dy, bit, letter in DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if visited[ny][nx]:
                            self.grid[y][x] &= ~bit
                            self.grid[ny][nx] &= ~OPPOSITE[letter]
                            visited[y][x] = True
                            break
                # If still isolated, force connection to the first neighbour
                if not visited[y][x]:
                    for dx, dy, bit, letter in DIRS:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            self.grid[y][x] &= ~bit
                            self.grid[ny][nx] &= ~OPPOSITE[letter]
                            visited[y][x] = True
                            break

    # ------------------------------------------------------------------
    # Loop injection (for non-perfect mazes)
    # ------------------------------------------------------------------

    def _add_loops(self) -> None:
        """Randomly open about 10% of interior walls to create loops."""
        target = max(1, (self.width * self.height) // 10)
        attempts = target * 10
        removed = 0
        for _ in range(attempts):
            if removed >= target:
                break
            x = self._rng.randrange(self.width)
            y = self._rng.randrange(self.height)
            if (x, y) in self.forty_two_cells:
                continue
            dx, dy, bit, letter = self._rng.choice(DIRS)
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            if (nx, ny) in self.forty_two_cells:
                continue
            # Do not open outer border walls
            if self._is_border_wall(x, y, bit):
                continue
            if self.grid[y][x] & bit:
                self.grid[y][x] &= ~bit
                self.grid[ny][nx] &= ~OPPOSITE[letter]
                removed += 1

    def _is_border_wall(self, x: int, y: int, bit: int) -> bool:
        """Return True if the wall bit is on the outer border."""
        if bit == 1 and y == 0:
            return True
        if bit == 4 and y == self.height - 1:
            return True
        if bit == 8 and x == 0:
            return True
        if bit == 2 and x == self.width - 1:
            return True
        return False

    # ------------------------------------------------------------------
    # Enforce corridor width ≤ 2
    # ------------------------------------------------------------------

    def _fix_wide_open(self) -> None:
        """Break any 3x3 fully open area by adding a wall between center
        and bottom."""
        max_passes = self.width * self.height
        for _ in range(max_passes):
            fixed_any = False
            for y in range(self.height - 2):
                for x in range(self.width - 2):
                    if self._is_3x3_open(x, y):
                        # Add a wall between center and the cell below
                        cx, cy = x + 1, y + 1
                        self.grid[cy][cx] |= 4
                        self.grid[cy + 1][cx] |= 1
                        fixed_any = True
            if not fixed_any:
                break

    def _is_3x3_open(self, ox: int, oy: int) -> bool:
        """Check if the 3x3 block starting at (ox, oy)
        has no internal walls."""
        for y in range(oy, oy + 3):
            for x in range(ox, ox + 2):
                if self.grid[y][x] & 2:  # east wall exists → not fully open
                    return False
        for y in range(oy, oy + 2):
            for x in range(ox, ox + 3):
                if self.grid[y][x] & 4:  # south wall exists
                    return False
        return True

    # ------------------------------------------------------------------
    # Wall symmetry enforcement
    # ------------------------------------------------------------------

    def _sync_walls(self) -> None:
        """
        Ensure that for every adjacent cell pair, the wall bits are consistent.

        This is done by scanning and
        setting the opposite wall bit for each cell.
        After that, we re-seal all "42" cells
        """
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                # North neighbour
                if y > 0:
                    if cell & 1:
                        self.grid[y - 1][x] |= 4
                    else:
                        self.grid[y - 1][x] &= ~4
                # East neighbour
                if x < self.width - 1:
                    if cell & 2:
                        self.grid[y][x + 1] |= 8
                    else:
                        self.grid[y][x + 1] &= ~8
                # South neighbour
                if y < self.height - 1:
                    if cell & 4:
                        self.grid[y + 1][x] |= 1
                    else:
                        self.grid[y + 1][x] &= ~1
                # West neighbour
                if x > 0:
                    if cell & 8:
                        self.grid[y][x - 1] |= 2
                    else:
                        self.grid[y][x - 1] &= ~2

        # Re-seal all 42 cells (they must be completely closed)
        for cx, cy in self.forty_two_cells:
            self.grid[cy][cx] |= 15

    # ------------------------------------------------------------------
    # BFS shortest path
    # ------------------------------------------------------------------

    def _bfs_path(self) -> List[str]:
        """Return the shortest path from entry to exit as a list of letters."""
        sx, sy = self.entry
        ex, ey = self.exit

        # Type: cell -> (parent_cell, direction_letter) or None for start
        prev: Dict[Tuple[int, int], Optional[Tuple[Tuple[int, int], str]]] = {}
        prev[(sx, sy)] = None
        queue = deque([(sx, sy)])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == (ex, ey):
                break
            for dx, dy, bit, letter in DIRS:
                if self.grid[cy][cx] & bit:
                    continue
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in prev:
                        prev[(nx, ny)] = ((cx, cy), letter)
                        queue.append((nx, ny))
        else:
            # No path found
            return []

        # Reconstruct path
        path: List[str] = []
        cur = (ex, ey)
        while True:
            item = prev[cur]
            if item is None:
                break
            parent, letter = item
            path.append(letter)
            cur = parent
        path.reverse()
        return path
