#!/usr/bin/env python3
"""
a_maze_ing.py - A-Maze-ing main program.

This script:
1.  reads a configuration file
2.  generates a maze using the MazeGenerator class,
3.  writes the output file, and
4.  launches an interactive terminal
    display with single-key commands.

Usage:
    python3 a_maze_ing.py config.txt
"""

import os
import sys
from typing import Dict, Optional, Tuple, TypedDict

from mazegen import MazeGenerator

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"

_WALL_CODES = [
    "\033[37m",  # White
    "\033[36m",  # Cyan
    "\033[32m",  # Green
    "\033[33m",  # Yellow
    "\033[35m",  # Magenta
    "\033[31m",  # Red
    "\033[34m",  # Blue
]
_WALL_NAMES = ["White", "Cyan", "Green", "Yellow", "Magenta", "Red", "Blue"]

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"


def _clr(text: str, code: str) -> str:
    """Wrap text with an ANSI colour code and reset."""
    return f"{code}{text}{RESET}"


def _clear_screen() -> None:
    """Clear the terminal using ANSI escape sequence."""
    print("\033[2J\033[H", end="", flush=True)


# ---------------------------------------------------------------------------
# Single-key input (no Enter required)
# ---------------------------------------------------------------------------


def _getch() -> str:
    """
    Read one character from stdin without waiting for Enter.

    Falls back to input() on systems without tty/termios (e.g., Windows).
    """
    try:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch
    except Exception:
        try:
            line = input()
            return line[0] if line else ""
        except EOFError:
            return "q"


# ---------------------------------------------------------------------------
# TypedDict for configuration
# ---------------------------------------------------------------------------

class ConfigDict(TypedDict):
    """Type definition for the configuration dictionary."""
    WIDTH: int
    HEIGHT: int
    ENTRY: Tuple[int, int]
    EXIT: Tuple[int, int]
    OUTPUT_FILE: str
    PERFECT: bool
    SEED: Optional[int]


# ---------------------------------------------------------------------------
# ASCII renderer with colours
# ---------------------------------------------------------------------------


def render(
    gen: MazeGenerator,
    show_path: bool = False,
    wall_code: str = "\033[37m",
) -> str:
    """
    Render the maze with coloured walls, entry/exit, path, and 42 cells.

    Symbols:
        S - entry (bold green)
        E - exit (bold red)
        . - solution path (yellow)
        ### - "42" cells (bold cyan)

    Args:
        gen: Generated maze instance.
        show_path: If True, overlay the solution path.
        wall_code: ANSI colour code for walls.

    Returns:
        Multi-line string ready for printing.
    """
    W, H = gen.width, gen.height

    # Build set of path cells for overlay
    path_cells = set()
    if show_path and gen.path:
        cx, cy = gen.entry
        path_cells.add((cx, cy))
        dm = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
        for letter in gen.path:
            dx, dy = dm[letter]
            cx += dx
            cy += dy
            path_cells.add((cx, cy))

    def wall(s: str) -> str:
        return _clr(s, wall_code)

    lines = []
    for gy in range(2 * H + 1):
        if gy % 2 == 0:
            # Horizontal wall row
            cy = gy // 2
            row = wall("+")
            for gx in range(W):
                if cy == 0:
                    has = bool(gen.grid[0][gx] & 1)
                elif cy == H:
                    has = bool(gen.grid[H - 1][gx] & 4)
                else:
                    has = bool(gen.grid[cy][gx] & 1)
                row += wall("---+" if has else "   +")
        else:
            # Cell row
            cy = gy // 2
            row = ""
            for gx in range(W):
                row += wall("|" if (gen.grid[cy][gx] & 8) else " ")

                if (gx, cy) == gen.entry:
                    row += _clr(" S ", _GREEN + BOLD)
                elif (gx, cy) == gen.exit:
                    row += _clr(" E ", _RED + BOLD)
                elif (gx, cy) in gen.forty_two_cells:
                    row += _clr("###", _CYAN + BOLD)
                elif show_path and (gx, cy) in path_cells:
                    row += _clr(" . ", _YELLOW)
                else:
                    row += "   "

            row += wall("|" if (gen.grid[cy][W - 1] & 2) else " ")

        lines.append(row)

    return "\n".join(lines)


def _status_bar(
    gen: MazeGenerator,
    show_path: bool,
    wall_idx: int,
    config: ConfigDict,
) -> str:
    """Build the status/help line shown below the maze."""
    seed_str = str(gen.seed) if gen.seed is not None else "random"
    path_state = "ON" if show_path else "off"
    color_name = _WALL_NAMES[wall_idx % len(_WALL_NAMES)]
    dim = f"{config['WIDTH']}x{config['HEIGHT']}"
    return (
        f"\n{BOLD}A-Maze-ing{RESET}  {dim}  seed={seed_str}  "
        f"path={path_state}  color={color_name}\n"
        "  [r] Random   [R] Seeded   [p] Path   [c] Color   [q] Quit\n"
    )


# ---------------------------------------------------------------------------
# Configuration parsing
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}


def parse_config(path: str) -> ConfigDict:
    """
    Parse a KEY=VALUE configuration file.

    Lines starting with '#' and blank lines are ignored.

    Args:
        path: Path to the config file.

    Returns:
        ConfigDict with typed values.

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: Syntax error, missing keys, invalid values.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path!r}")

    raw: Dict[str, str] = {}
    with open(path, "r") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(
                    f"Line {lineno}: expected 'KEY=VALUE', got {line!r}"
                )
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not key:
                raise ValueError(f"Line {lineno}: empty key.")
            if not value:
                raise ValueError(
                    f"Line {lineno}: empty value for key '{key}'."
                                )
            if key in raw:
                print(
                    f"Warning: duplicate key '{key}' on line {lineno}"
                    f" - using last value."
                )
            raw[key] = value

    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        raise ValueError(
            f"Missing required keys: {', '.join(sorted(missing))}"
        )

    # Parse integers
    try:
        width = int(raw["WIDTH"])
        height = int(raw["HEIGHT"])
    except ValueError:
        raise ValueError("WIDTH and HEIGHT must be integers.")
    if width < 2 or height < 2:
        raise ValueError(
            f"WIDTH and HEIGHT must each be at least 3 (got {width}x{height})."
        )

    # Parse coordinates
    def _coord(val: str, name: str) -> Tuple[int, int]:
        parts = val.split(",")
        if len(parts) != 2:
            raise ValueError(f"{name} must be 'x,y', got {val!r}")
        try:
            x = int(parts[0].strip())
            y = int(parts[1].strip())
        except ValueError:
            raise ValueError(f"{name} contains non-integer values: {val!r}")
        return x, y

    entry = _coord(raw["ENTRY"], "ENTRY")
    exit_ = _coord(raw["EXIT"], "EXIT")

    # PERFECT (boolean)
    pval = raw["PERFECT"].lower()
    if pval in ("true", "1", "yes", "on"):
        perfect = True
    elif pval in ("false", "0", "no", "off"):
        perfect = False
    else:
        raise ValueError(
            f"PERFECT must be True or False, got {raw['PERFECT']!r}"
        )

    # SEED (optional)
    seed: Optional[int] = None
    if "SEED" in raw and raw["SEED"]:
        try:
            seed = int(raw["SEED"])
        except ValueError:
            raise ValueError(f"SEED must be an integer, got {raw['SEED']!r}")

    return {
        "WIDTH": width,
        "HEIGHT": height,
        "ENTRY": entry,
        "EXIT": exit_,
        "OUTPUT_FILE": raw["OUTPUT_FILE"],
        "PERFECT": perfect,
        "SEED": seed,
    }


# ---------------------------------------------------------------------------
# Interactive loop
# ---------------------------------------------------------------------------


def run_display(
    gen: MazeGenerator,
    config: ConfigDict,
    output_path: str,
) -> None:
    """
    Interactive terminal loop with commands:

        r - regenerate with new random seed
        R - regenerate with stored seed
        p - toggle solution path
        c - cycle wall colours
        q / Esc / Ctrl-C - quit
    """
    show_path = False
    wall_idx = 0

    while True:
        _clear_screen()
        print(render(gen, show_path, _WALL_CODES[wall_idx]))
        print(_status_bar(gen, show_path, wall_idx, config), end="")

        try:
            key = _getch()
        except KeyboardInterrupt:
            break

        if key in ("q", "\x1b", "\x03"):
            break

        if key == "r":
            # Regenerate with a new random seed (ignore stored)
            gen = MazeGenerator(
                width=config["WIDTH"],
                height=config["HEIGHT"],
                entry=config["ENTRY"],
                exit_=config["EXIT"],
                perfect=config["PERFECT"],
                seed=None,
            )
            show_path = False
            try:
                gen.export_to_file(output_path)
            except OSError as exc:
                print(f"Warning: could not update output file: {exc}")

        elif key == "R":
            # Regenerate with the stored seed (if any)
            gen = MazeGenerator(
                width=config["WIDTH"],
                height=config["HEIGHT"],
                entry=config["ENTRY"],
                exit_=config["EXIT"],
                perfect=config["PERFECT"],
                seed=config["SEED"],
            )
            show_path = False
            try:
                gen.export_to_file(output_path)
            except OSError as exc:
                print(f"Warning: could not update output file: {exc}")

        elif key == "p":
            show_path = not show_path

        elif key == "c":
            wall_idx = (wall_idx + 1) % len(_WALL_CODES)

    print("Bye.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse config, generate maze, write output, launch interactive visual."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]

    try:
        config = parse_config(config_path)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as exc:
        print(f"Error: Cannot read {config_path!r}: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Configuration:")
    print(f"  Dimensions : {config['WIDTH']}x{config['HEIGHT']}")
    print(f"  Entry      : {config['ENTRY']}")
    print(f"  Exit       : {config['EXIT']}")
    print(f"  Perfect    : {config['PERFECT']}")
    seed_display = config["SEED"] if config["SEED"] is not None else "random"
    print(f"  Seed       : {seed_display}")
    print(f"  Output     : {config['OUTPUT_FILE']}")

    try:
        gen = MazeGenerator(
            width=config["WIDTH"],
            height=config["HEIGHT"],
            entry=config["ENTRY"],
            exit_=config["EXIT"],
            perfect=config["PERFECT"],
            seed=config["SEED"],
        )
    except (ValueError, RuntimeError) as exc:
        print(f"Generation error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        gen.export_to_file(config["OUTPUT_FILE"])
        print(f"Maze written to {config['OUTPUT_FILE']!r}")
    except OSError as exc:
        print(f"Output error: {exc}", file=sys.stderr)
        sys.exit(1)

    # If stdout is not a terminal or NO_DISPLAY is set, just print plain ASCII
    if not sys.stdout.isatty() or os.environ.get("NO_DISPLAY"):
        print("\nASCII representation:")
        print(gen.display_ascii(show_path=False))
        return

    run_display(gen, config, config["OUTPUT_FILE"])


if __name__ == "__main__":
    main()
