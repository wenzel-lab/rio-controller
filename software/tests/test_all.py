#!/usr/bin/env python3
"""
Run all tests in the test suite.

This script discovers and runs all test modules in the tests/ directory.

Usage:
    python tests/test_all.py
    python -m tests.test_all
"""

import sys
import os
import unittest

# Set simulation mode for all tests
os.environ["RIO_SIMULATION"] = "true"

# Add parent directory (software/) to path
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_dir not in sys.path:
    sys.path.insert(0, software_dir)


def discover_and_run_tests():
    """Discover and run all tests"""
    # Discover tests in the tests directory
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(__file__), pattern="test_*.py", top_level_dir=software_dir
    )

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(discover_and_run_tests())
