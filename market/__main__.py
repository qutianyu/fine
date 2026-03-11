#!/usr/bin/env python3
"""
Fine CLI Entry Point

Usage:
    python -m fine run --config client_config.json
    python -m fine backtest --config backtest.json
    python -m fine indicator --config indicator.json
    python -m fine data --config data.json
"""

import sys
from fine.market_data.cli import main

if __name__ == "__main__":
    sys.exit(main())
