_This project has been created as part of the 42 curriculum by **laraus** and **adrramos**._

# A‑Maze‑ing

## Description

A‑Maze‑ing is a Python maze generator that reads a configuration file, builds a random maze (perfect or imperfect) using an iterative Depth‑First Search algorithm, exports it in a hexadecimal wall‑encoding format, and provides an interactive terminal display with coloured walls, a toggleable solution path, and live regeneration commands.

The project is split into a reusable `MazeGenerator` module (`mazegen.py`) and a main program (`a_maze_ing.py`) that handles configuration, file I/O, and the user interface.


## Installation & Usage

### Requirements
- Python 3.10 or higher
- `make` (optional)
- `pip`

### Setup
```bash
git clone <repository-url>
cd A-Maze-ing
make install
```
This creates a virtual environment, installs the package in editable mode, and adds development dependencies (`flake8`, `mypy`, `black`, `autopep8`, `build`).

### Run
```bash
make run
```
or directly:
```bash
python3 a_maze_ing.py config.txt
```

### Makefile Targets
| Target            | Description                                           |
|-------------------|-------------------------------------------------------|
| `make install`    | Set up virtual environment and dependencies.          |
| `make run`        | Run with default `config.txt`.                       |
| `make debug`      | Run with `pdb`.                                      |
| `make clean`      | Remove caches, virtual environments, build artifacts.|
| `make lint`       | Run `flake8` and `mypy` (with mandatory flags).      |
| `make build`      | Build distribution wheel and source tarball.         |
| `make format`     | Format code with `black`.                            |
| `make fix`        | Auto‑fix style issues with `autopep8`.               |


## Configuration File

The configuration file uses `KEY=VALUE` pairs (one per line). Lines starting with `#` are ignored.

| Key          | Description                           | Example      |
|--------------|---------------------------------------|--------------|
| `WIDTH`      | Number of columns (≥ 3)               | `WIDTH=20`   |
| `HEIGHT`     | Number of rows (≥ 3)                  | `HEIGHT=15`  |
| `ENTRY`      | Entry coordinates `x,y`               | `ENTRY=0,0`  |
| `EXIT`       | Exit coordinates `x,y`                | `EXIT=19,14` |
| `OUTPUT_FILE`| Output filename                       | `OUTPUT_FILE=maze.txt` |
| `PERFECT`    | `True` or `False` (unique path / loops) | `PERFECT=True` |
| `SEED`       | Optional integer seed                 | `SEED=42`    |

### Example
```ini
WIDTH=10
HEIGHT=10
ENTRY=1,1
EXIT=6,7
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
```


## Features & Compliance

| Subject Requirement | Implementation |
|---------------------|----------------|
| Python 3.10+        | Entire project uses Python 3.10 |
| Main file `a_maze_ing.py` | Mandatory filename respected |
| Config file support | `parse_config()` validates required keys, types, ranges |
| Random maze generation | Iterative DFS with `random.Random` |
| Seed reproducibility | `random.Random(seed)` |
| Perfect maze support | DFS produces spanning tree |
| Imperfect maze support | `_add_loops()` introduces ~10% extra passages |
| Entry & exit validation | Bounds check, not equal, not overlapping “42” pattern |
| Wall consistency | `_sync_walls()` enforces symmetry between adjacent cells |
| Border walls enforced | Outer cells remain fully closed |
| “42” pattern visible | `_place_forty_two()` draws fixed bitmap in the centre |
| No 3×3 open areas | `_fix_wide_open()` breaks large open spaces |
| Shortest path output | BFS (`_bfs_path()`) returns direction letters |
| Hexadecimal export | `export_to_file()` writes hex grid, blank line, entry, exit, path |
| Terminal visualisation | `render()` with ANSI colours, interactive commands |
| Path toggle | `p` key |
| Regeneration | `r` (random) and `R` (seeded) keys |
| Colour change | `c` key cycles 7 colours |
| Reusable class | `MazeGenerator` in `mazegen.py` |
| Type hints & docstrings | Entire codebase typed and documented (PEP257) |
| `mypy`/`flake8` compliance | `make lint` passes |
| Graceful exception handling | All expected errors caught; no uncontrolled crashes |
| Makefile | All mandatory targets present |
| `.gitignore` | Excludes Python artifacts, caches, virtual environments |


## Project Structure

```
A-Maze-ing/
├── a_maze_ing.py          # CLI entry point
├── mazegen.py             # Core MazeGenerator class
├── config.txt             # Default configuration
├── Makefile               # Task automation
├── pyproject.toml         # Package metadata
├── README.md              # This file
├── .gitignore
├── mazegen-*.whl          # Built wheel
├── mazegen-*.tar.gz       # Source tarball
└── tests/                 # (Optional) Unit tests
```


## Algorithm & Internal Representation

### Maze Representation
The maze is a two‑dimensional grid: `grid[y][x]`. Each cell is an integer from `0` to `15`, where each bit represents a closed wall:

| Bit | Direction | Value |
|-----|-----------|-------|
| 0   | North     | 1     |
| 1   | East      | 2     |
| 2   | South     | 4     |
| 3   | West      | 8     |

A wall is **closed** when its bit is `1`, **open** when `0`.  
Example: `9` (binary `1001`) → North and West closed, East and South open.

**Why bitmasking?**  
- Memory efficient (one integer stores four walls)  
- Fast bitwise operations  
- Direct mapping to hexadecimal – each digit (0‑F) exactly represents one cell.

### Generation: Iterative DFS (Recursive Backtracker)
- Start at entry, mark visited.  
- While unvisited cells remain:  
  - Look at current cell’s unvisited neighbours.  
  - Choose one randomly, remove the wall between them, push the neighbour onto a stack.  
  - If no unvisited neighbour, pop the stack (backtrack).  
- Result is a perfect maze (spanning tree) when `PERFECT=True`.

### Pathfinding: BFS
The maze is an unweighted graph; BFS guarantees the shortest path. The solution is stored as a string of direction letters: `N`, `E`, `S`, `W` (no spaces). It is written to the output file after the entry/exit coordinates.

### Additional Constraints
- **“42” pattern** – a fixed set of closed cells is placed in the centre (if the maze is large enough).  
- **No 3×3 open areas** – `_fix_wide_open()` scans and breaks any fully open 3×3 block.  
- **Wall symmetry** – `_sync_walls()` does not create or remove maze passages.
It copies each wall state to the neighbouring cell so that
both sides of every shared wall are represented consistently.
- **Imperfect mode** – when `PERFECT=False`, about 10% of interior walls are randomly opened to create loops.

### Output File Format
```
<hex grid, row by row, digits separated by spaces or not>
<blank line>
<entry x,y>
<exit x,y>
<solution letters, e.g. EESSW>
```


## Defensive Programming & Testing

| Risk | Protection |
|------|------------|
| Missing config file | `os.path.isfile()` check |
| Invalid keys / types | `REQUIRED_KEYS` validation; type conversion with error messages |
| Invalid coordinates | Bounds checking |
| Entry == Exit | Explicit `!=` check |
| Dimensions < 3 | Minimum size validation |
| Invalid booleans | Parse true/1/yes/on; default to `False` |
| File write failures | `try/except` around output operations |
| Keyboard interruption (Ctrl‑C) | Graceful exit |
| EOF (Ctrl‑D) in interactive mode | Handled via `EOFError`; exits cleanly |
| Wall inconsistencies | `_sync_walls()` ensures symmetry |
| Isolated cells | `_reconnect_isolated()` force‑connects any cut‑off cells |
| 42 overlap | `_place_forty_two()` checks entry/exit coordinates |

All file operations use context managers (`with`). Exceptions are caught at the top level and printed to stderr, so the program **does not crash unexpectedly**.

### Interactive Commands
- `r` – regenerate with a new random seed  
- `R` – regenerate with the same seed (restore reproducibility)  
- `p` – toggle solution path overlay  
- `c` – cycle through 7 wall colours  
- `q` or `Esc` – quit  
- `Ctrl‑C` / `Ctrl‑D` – exit gracefully


## Reusable Module

The `mazegen.py` module can be installed and used independently:

```bash
make build                # creates dist/mazegen-*.whl
pip install mazegen-*.whl
```

Then in any Python script:
```python
from mazegen import MazeGenerator

gen = MazeGenerator(width=10, height=10, entry=(0,0), exit_=(9,9), perfect=True, seed=42)
gen.export_to_file("my_maze.txt")
print(gen.display_ascii(show_path=True))
print(gen.get_solution_letters())   # e.g., "EESSW..."
```


## Resources
- [Wikipedia – Maze generation algorithm](https://en.wikipedia.org/wiki/Maze_generation_algorithm)  
- [Mazes for Programmers – Jamis Buck](https://pragprog.com/titles/jbmaze/mazes-for-programmers/)  
- [Python `random` documentation](https://docs.python.org/3/library/random.html)  
- [PEP 257 – Docstring conventions](https://peps.python.org/pep-0257/)

AI‑assisted tools (ChatGPT, GitHub Copilot) were used for boilerplate, docstrings, and debugging; all suggestions were reviewed and adapted to ensure correctness and compliance.


**Team**  
- **laraus** – Core algorithm, defensive programming, logic, and overall structure.  
- **adrramos** – User interface, packaging, configuration parser, and Makefile.

