import os
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent

# Many legacy tests use paths like "equi/vasp/CONTCAR" relative to the
# tests directory. Normalize the working directory once when the package is
# imported through `python -m unittest tests...`.
os.chdir(TESTS_DIR)
