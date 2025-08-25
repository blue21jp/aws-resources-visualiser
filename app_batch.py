#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - バッチ処理実行用ラッパー"""

# First Party Library
from app.batch.main import main

if __name__ == "__main__":
    # clickデコレータ付きのmain()を直接実行
    main()
