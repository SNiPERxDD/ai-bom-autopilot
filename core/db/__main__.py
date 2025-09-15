#!/usr/bin/env python3
"""
Migration runner entry point for python -m core.db.migrations
"""

from .migrations import migration_runner

if __name__ == "__main__":
    migration_runner()