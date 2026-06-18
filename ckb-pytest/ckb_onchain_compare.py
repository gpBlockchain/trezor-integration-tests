#!/usr/bin/env python3
"""Compatibility wrapper for the object-based onchain_compare CLI."""

from onchain_compare.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
