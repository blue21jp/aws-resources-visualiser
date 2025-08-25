#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - 設定管理"""

# Standard Library
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

SUPPORTED_REGIONS: List[str] = [
    "us-east-1",
    "ap-northeast-1",
]

SUPPORTED_SERVICES: Dict[str, str] = {
    "EC2": "Amazon Elastic Compute Cloud",
    "RDS": "Amazon Relational Database Service",
    "S3": "Amazon Simple Storage Service",
    "Lambda": "AWS Lambda",
}

REQUIRED_TAGS: List[str] = [
    "CostProject",
]

CHART_COLORS: Dict[str, str] = {
    "success": "#2ca02c",
    "danger": "#d62728",
}

STREAMLIT_CONFIG: Dict[str, Any] = {
    "page_title": "AWS Resource Visualizer",
    "page_icon": "☁️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# キャッシュ設定
CACHE_TTL: int = 86400  # 24時間
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR: str = str(PROJECT_ROOT / "cache")

ESTIMATED_COSTS: Dict[str, float] = {
    "EC2": 50.0,
    "RDS": 100.0,
    "S3": 5.0,
    "Lambda": 1.0,
}

COST_CALCULATION_INFO: Dict[str, str] = {
    "EC2": "t3.medium インスタンス（2vCPU, 4GB RAM）を24時間稼働想定",
    "RDS": "db.t3.micro インスタンス（MySQL）を24時間稼働想定",
    "S3": "Standard ストレージクラス 100GB 保存想定",
    "Lambda": "月間100万リクエスト、平均実行時間100ms想定",
}

COST_DISCLAIMER: str = """
**概算コスト計算について**

この概算コストは以下の前提条件に基づく参考値です：

• **計算式**: リソース数 × 各サービスの月額想定コスト
• **料金体系**: 2024年時点のus-east-1リージョンの料金を基準
• **想定使用量**: 一般的な使用パターンを仮定

**重要な注意事項**:
- 実際の料金は使用量、リージョン、インスタンスタイプ等により大きく変動します
- Reserved Instance、Savings Plans等の割引は考慮されていません
- データ転送料金、追加ストレージ料金等は含まれていません
- 正確な見積もりは [AWS Pricing Calculator](https://calculator.aws) をご利用ください
"""

PAGINATION_CONFIG: Dict[str, Any] = {
    "default_page_size": 10,
    "page_size_options": [5, 10, 20, 50, 100],
    "show_page_info": True,
    "show_total_count": True,
}

DEFAULT_REGION: str = "us-east-1"
DEFAULT_SERVICES: List[str] = list(SUPPORTED_SERVICES.keys())

AVAILABLE_PROFILES: List[str] = [
    "sandbox",
    "demo",
]
DEFAULT_PROFILE: str = "sandbox"

# AWS API ページネーション設定
AWS_API_CONFIG: Dict[str, Any] = {
    "max_resources_per_service": 1000,  # 各サービスで取得する最大リソース数
    "pagination_page_size": 100,  # デフォルトページサイズ
    # サービス別ページサイズ設定（APIの制限に合わせて調整）
    "service_page_sizes": {
        "EC2": 1000,  # EC2の最大ページサイズ
        "RDS": 100,  # RDSの推奨ページサイズ
        "S3": 1000,  # S3の最大ページサイズ
        "Lambda": 50,  # Lambdaの最大ページサイズ（APIハードリミット）
    },
}

# 実行環境設定
# BATCH_RUN_TYPE: poetry, docker, ecs のいずれかを指定
# デフォルトは poetry
BATCH_RUN_TYPE: str = os.getenv("BATCH_RUN_TYPE", "poetry").lower()


def get_effective_region(region: str) -> str:
    """実行環境に応じた有効なリージョンを取得

    Args:
        region: 指定されたリージョン

    Returns:
        str: 有効なリージョン
            - ECS環境: 環境変数AWS_DEFAULT_REGIONまたはDEFAULT_REGION
            - その他: 指定されたリージョン
    """
    if BATCH_RUN_TYPE == "ecs":
        return os.environ.get("AWS_DEFAULT_REGION", DEFAULT_REGION)
    else:
        return region


def get_effective_profile(profile: Optional[str]) -> Optional[str]:
    """実行環境に応じた有効なプロファイルを取得

    Args:
        profile: 指定されたプロファイル

    Returns:
        Optional[str]: 有効なプロファイル
            - ECS環境: None（IAMロール使用）
            - その他: 指定されたプロファイル
    """
    if BATCH_RUN_TYPE == "ecs":
        return None
    else:
        return profile


def should_use_profile_in_command(profile: Optional[str]) -> bool:
    """コマンドラインでプロファイルを使用すべきかを判定

    Args:
        profile: 指定されたプロファイル

    Returns:
        bool: プロファイルを使用すべきかどうか
            - Poetry・Docker環境でプロファイルが指定されている場合: True
            - その他: False
    """
    return BATCH_RUN_TYPE in ["poetry", "docker"] and profile is not None


def should_use_region_in_command() -> bool:
    """コマンドラインでリージョンを使用すべきかを判定

    Returns:
        bool: リージョンを使用すべきかどうか
            - Poetry・Docker環境: True
            - その他: False
    """
    return BATCH_RUN_TYPE in ["poetry", "docker"]


# バッチ処理ログ設定
BATCH_LOG_CONFIG: Dict[str, Any] = {
    "log_dir": os.environ.get(
        "AWS_RESOURCE_VISUALIZER_LOG_DIR",
        str(PROJECT_ROOT / "logs"),
    ),
    "log_filename": "batch_execution.log",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(levelname)s - %(message)s",
    "enable_console_output": False,  # True:標準出力にもログを出力
    "overwrite_on_start": False,  # ローテート使用時はFalseに変更
    # ログローテート設定
    "rotation_type": "time",  # 時間ベースローテート
    "when": "midnight",  # 毎日午前0時
    "interval": 1,  # 1日間隔
    "backup_count": 7,  # 7日分保持
    "date_suffix": "%Y-%m-%d",  # 日付フォーマット（例: batch_execution.log.2025-08-20）
}

# バッチ処理並列実行設定
MAX_CONCURRENT_SERVICES: int = 5  # 同時実行するサービス数の上限

# 自動更新間隔（秒）
AUTO_REFRESH_INTERVAL: int = 5
