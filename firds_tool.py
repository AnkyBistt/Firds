#!/usr/bin/env python3
"""
FIRDS DLTINS Reference Data Inspector & Reconciler Launcher.
"""

import sys
from pathlib import Path

# Add current folder to sys.path to allow module imports
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from firds_inspector.cli import main

if __name__ == "__main__":
    main()
