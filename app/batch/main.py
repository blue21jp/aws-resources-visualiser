#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - バッチアプリケーション メイン"""

# Standard Library
import asyncio
import json
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import List, Tuple

# Third Party Library
import click

# First Party Library
from app.shared.config import (
    BATCH_LOG_CONFIG,
    DEFAULT_REGION,
    SUPPORTED_SERVICES,
)
from app.shared.state_manager import get_state_manager

# Local Library
from .data_fetcher import DataFetcher


def setup_logging() -> logging.Logger:
    """ログ設定を初期化"""
    # ログディレクトリを作成
    log_dir = Path(BATCH_LOG_CONFIG["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイルパス
    log_file = log_dir / BATCH_LOG_CONFIG["log_filename"]

    # ログハンドラーを設定
    handlers: List[logging.Handler] = []

    # ファイルハンドラー（ローテート対応）
    file_handler: logging.Handler
    if BATCH_LOG_CONFIG.get("rotation_type") == "time":
        # 時間ベースローテート
        rotating_handler = TimedRotatingFileHandler(
            log_file,
            when=BATCH_LOG_CONFIG["when"],
            interval=BATCH_LOG_CONFIG["interval"],
            backupCount=BATCH_LOG_CONFIG["backup_count"],
            encoding="utf-8",
        )
        # 日付サフィックスを設定（ログファイル名に日付を付与）
        rotating_handler.suffix = BATCH_LOG_CONFIG["date_suffix"]
        file_handler = rotating_handler
    else:
        # 従来のファイルハンドラー（後方互換性）
        if (
            BATCH_LOG_CONFIG.get("overwrite_on_start", False)
            and log_file.exists()
        ):
            log_file.unlink()  # 既存ファイルを削除
        file_handler = logging.FileHandler(log_file, mode="w")

    file_handler.setLevel(getattr(logging, BATCH_LOG_CONFIG["log_level"]))
    file_handler.setFormatter(
        logging.Formatter(BATCH_LOG_CONFIG["log_format"])
    )
    handlers.append(file_handler)

    # コンソールハンドラー（標準出力も維持）
    if BATCH_LOG_CONFIG["enable_console_output"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            getattr(logging, BATCH_LOG_CONFIG["log_level"])
        )
        console_handler.setFormatter(
            logging.Formatter(BATCH_LOG_CONFIG["log_format"])
        )
        handlers.append(console_handler)

    # ロガーを設定
    logger = logging.getLogger("batch_main")
    logger.setLevel(getattr(logging, BATCH_LOG_CONFIG["log_level"]))

    # 既存のハンドラーをクリア
    logger.handlers.clear()

    # 新しいハンドラーを追加
    for handler in handlers:
        logger.addHandler(handler)

    # ログファイルパスを出力
    logger.info(f"ログファイル: {log_file}")

    return logger


@click.command()
@click.option(
    "--services",
    multiple=True,
    type=click.Choice(list(SUPPORTED_SERVICES.keys())),
    default=list(SUPPORTED_SERVICES.keys()),
    help="取得するサービス",
)
@click.option(
    "--region",
    type=str,
    help="AWSリージョン（ローカル実行時は必須）",
)
@click.option(
    "--profile",
    type=str,
    help="AWSプロファイル（ローカル実行時のみ）",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="キャッシュをクリア",
)
@click.option(
    "--force",
    is_flag=True,
    help="ロックを無視して強制実行",
)
def main(
    services: Tuple[str, ...],
    region: str,
    profile: str,
    clear_cache: bool,
    force: bool,
) -> None:
    """AWS Resource Data Fetcher"""
    # servicesをリストに変換（既存コードとの互換性のため）
    services_list = list(services)

    # 非同期処理を実行
    asyncio.run(async_main(services_list, region, profile, clear_cache, force))


async def async_main(
    services: List[str],
    region: str,
    profile: str,
    clear_cache: bool,
    force: bool,
) -> None:
    """バッチアプリケーションのメイン処理"""
    # ログ設定を初期化
    logger = setup_logging()

    logger.info("=== AWS Resource Visualizer バッチ処理開始 ===")
    logger.info(
        f"引数: services={services}, region={region}, profile={profile}, clear_cache={clear_cache}, force={force}"
    )

    # リージョンの決定（ECS環境では環境変数から取得）
    if not region:
        # ECS環境では環境変数から取得
        region = os.environ.get("AWS_DEFAULT_REGION", DEFAULT_REGION)
        logger.info(f"リージョンを環境変数から取得: {region}")
    else:
        logger.info(f"リージョン指定: {region}")

    # ステータスマネージャーを取得
    state_manager = get_state_manager()

    # 重複実行チェック（forceオプションが指定されていない場合）
    if not force and state_manager.is_status_running(
        services, region, profile
    ):
        error_msg = "同じ条件でバッチが実行中です。--forceオプションで強制実行できます。"
        logger.error(error_msg)
        error_result = {
            "success": False,
            "error": error_msg,
            "services": services,
            "region": region,
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

    # 実行開始ステータスを記録（Web実行との重複防止）
    state_manager.start_execution_status(
        services, region, profile, pid=os.getpid()
    )

    try:
        logger.info(f"データ取得開始: {services} in {region}")
        await execute_data_fetch(
            services,
            state_manager,
            region,
            profile,
            clear_cache,
            force,
            logger,
        )

    except Exception as e:
        logger.error(f"バッチ処理でエラーが発生: {str(e)}", exc_info=True)

        # エラー時はステータスファイルに記録
        state_manager.finish_execution_failed(
            services, region, profile, str(e)
        )

        error_result = {
            "success": False,
            "error": str(e),
            "services": services,
            "region": region,
        }
        print(json.dumps(error_result, ensure_ascii=False))
        logger.error(f"エラー結果: {error_result}")
        sys.exit(1)

    logger.info("=== AWS Resource Visualizer バッチ処理終了 ===")


async def execute_data_fetch(
    services: List[str],
    state_manager,
    region: str,
    profile: str,
    clear_cache: bool,
    force: bool,
    logger: logging.Logger,
) -> None:
    """データ取得を実行"""
    logger.info("データ取得処理を開始")

    fetcher = DataFetcher(services=services, region=region, profile=profile)

    # キャッシュクリアをデータ取得前に実行
    if clear_cache:
        logger.info("キャッシュをクリア")
        fetcher.clear_cache()

    logger.info(f"対象サービス: {services}")
    results = await fetcher.fetch_all_data()

    success_count = sum(1 for df in results.values() if not df.empty)
    total_count = len(results)

    logger.info(f"データ取得完了: {success_count}/{total_count} サービス成功")

    # 各サービスの取得結果をログに記録
    for service, df in results.items():
        record_count = len(df)
        if record_count > 0:
            logger.info(f"  {service}: {record_count}件取得")
        else:
            logger.warning(f"  {service}: データ取得失敗またはデータなし")

    # 結果をJSONで出力（Webアプリとの連携用）
    result_summary = {
        "success": True,
        "services": services,
        "region": region,
        "success_count": success_count,
        "total_count": total_count,
        "results": {service: len(df) for service, df in results.items()},
    }

    # 成功時はステータスファイルに記録
    state_manager.finish_execution_success(
        services, region, profile, result_summary
    )

    print(json.dumps(result_summary, ensure_ascii=False))
    logger.info(f"成功結果: {result_summary}")


if __name__ == "__main__":
    main()
