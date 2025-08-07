#!/usr/bin/env python3
"""
Common test configuration and fixtures for the PrisMind project
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Common fixtures can be defined here and will be available to all test modules