# ============================================================================
# A-Maze-ing Makefile
# ============================================================================

# --- Configuration ----------------------------------------------------------

SYSTEM_PYTHON := python3.10
ENV_BIN       := .venv/bin
ENV_PY        := $(ENV_BIN)/python3
PIP           := $(ENV_BIN)/pip
MAIN       	  := a_maze_ing.py
CONFIG        := config.txt
CORE_FILES    := a_maze_ing.py mazegen.py

# Flags for mypy (exactly as required by the subject)
MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
              --ignore-missing-imports --disallow-untyped-defs \
              --check-untyped-defs

# --- Mandatory Targets (required by the subject) ----------------------------

# M: install - set up virtual environment and install the package + dev tools
install:
	$(SYSTEM_PYTHON) -m venv .venv
	$(ENV_PY) -m pip install --upgrade pip
	$(PIP) install -e .[dev]

# M: run - execute the main script with the default config
run:
	$(ENV_PY) $(MAIN) $(CONFIG)

# M: debug - run the main script with Python's debugger (pdb)
debug:
	$(ENV_PY) -m pdb $(MAIN) $(CONFIG)

# M: clean - remove caches, build artifacts, and virtual environments
clean:
	rm -rf __pycache__ */__pycache__
	rm -rf dist build *.egg-info
	find . -name .mypy_cache -type d -exec rm -rf {} +
	rm -f mazegen-*.whl
	rm -f mazegen-*.tar.gz

clean-all:
	rm -rf .venv .venv-user dist build *.egg-info .mypy_cache

# M: lint - check code style and types (mandatory flags)
lint:
	$(ENV_BIN)/flake8 . --exclude=.venv,.venv-user
	$(ENV_BIN)/mypy . $(MYPY_FLAGS)

# O: lint-strict - same as lint but with --strict (optional, recommended)
lint-strict:
	$(ENV_BIN)/flake8 . --exclude=.venv,.venv-user
	$(ENV_BIN)/mypy . --strict

# --- Optional / Extra Targets ------------------------------------------------

# O: install-user - install the pre-built wheel for the current user
install-user:
	$(SYSTEM_PYTHON) -m venv .venv-user
	.venv-user/bin/python3 -m pip install --upgrade pip
	.venv-user/bin/pip install mazegen-*.whl

# O: build - create a distribution wheel and source tarball
build: install
	$(ENV_PY) -m build
	rm -rf mazegen.egg-info
	@echo "Copying package artifacts to repository root..."
	cp dist/mazegen-*.whl .
	cp dist/mazegen-*.tar.gz .
	@echo "Copied:"
	@ls -1 mazegen-*.whl mazegen-*.tar.gz

# O: build-clean - remove package artifacts from root
build-clean:
	rm -f mazegen-*.whl
	rm -f mazegen-*.tar.gz

# O: build-all - clean, then build, then copy
build-all: clean build
	@echo "Build complete:"
	@ls -1 mazegen-*.whl mazegen-*.tar.gz

# O: re - clean and reinstall everything in one go
re: clean install

# O: fix - auto-fix formatting issues with autopep8
fix:
	$(ENV_BIN)/autopep8 --in-place --aggressive --aggressive $(CORE_FILES)
	@echo "Auto-fixed formatting issues"

# O: format - reformat code with Black
format:
	$(ENV_BIN)/black --target-version py310 $(CORE_FILES)
	@echo "Formatted with Black"

# O: snapshot - create a text snapshot of all source files for debugging
snapshot:
	@for f in $(CORE_FILES) config.txt Makefile pyproject.toml README.md \
	          .gitignore; do \
		echo "===== $$f ====="; \
		cat "$$f"; \
		echo; \
	done > project_snapshot.txt
	@echo "Snapshot saved to project_snapshot.txt"

# O: check-borders - a quick validation example (fixed import)
check-borders:
	@echo "check-borders removed"
	$(ENV_PY) -c '\
from mazegen import MazeGenerator; \
gen = MazeGenerator(10, 10, entry=(0,0), exit=(9,9), seed=42); \
gen.generate(perfect=True); \
grid = gen.get_grid(); \
print("Top:", [bool(grid[0][x] & 1) for x in range(10)]); \
print("Bottom:", [bool(grid[9][x] & 4) for x in range(10)])'

# ----------------------------------------------------------------------------
# Phony Targets (all declared together at the end)
# ----------------------------------------------------------------------------

.PHONY: install run debug clean lint lint-strict install-user build \
        build-clean build-all re fix format snapshot check-borders
		