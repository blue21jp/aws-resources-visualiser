#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - Streamlit実行用ラッパー"""

# Standard Library
import sys

# First Party Library
from app.web.app import main

# 標準出力のバッファリングを無効化
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

if __name__ == "__main__":
    main()
