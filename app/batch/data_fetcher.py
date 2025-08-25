#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - 非同期データ取得処理"""

# Standard Library
import asyncio
import logging
from typing import Dict, List, Optional

# Third Party Library
import pandas as pd

# First Party Library
from app.shared.aws_client import (
    get_ec2_instances,
    get_lambda_functions,
    get_rds_instances,
    get_s3_buckets,
)
from app.shared.cache_manager import get_cache_instance
from app.shared.config import MAX_CONCURRENT_SERVICES


class DataFetcher:
    """非同期データ取得クラス"""

    def __init__(
        self, services: List[str], region: str, profile: Optional[str] = None
    ):
        self.services = services
        self.region = region
        self.profile = profile
        self.cache = get_cache_instance()
        self.logger = logging.getLogger("batch_main")

    def clear_cache(self) -> None:
        """指定されたprofile・regionの全サービスキャッシュをクリア"""
        # First Party Library
        from app.shared.config import SUPPORTED_SERVICES

        cleared_count = 0
        # 指定されたサービスではなく、全サポートサービスのキャッシュを削除
        for service in SUPPORTED_SERVICES.keys():
            result = self.cache.clear_cache(service, self.region, self.profile)
            if result > 0:
                cleared_count += result
                self.logger.info(f"{service}のキャッシュを削除")
            else:
                self.logger.debug(
                    f"{service}のキャッシュファイルは存在しません"
                )

        self.logger.info(
            f"全サービスキャッシュクリア完了: profile={self.profile}, region={self.region}, 削除ファイル数={cleared_count}"
        )

    async def fetch_service_data(self, service: str) -> pd.DataFrame:
        """個別サービスのデータを非同期取得"""
        self.logger.info(f"{service} データ取得開始")

        # キャッシュチェック
        cached_data = self.cache.get_cached_data(
            service, self.region, self.profile
        )
        if cached_data is not None:
            self.logger.info(
                f"{service} キャッシュからデータを取得 ({len(cached_data)}件)"
            )
            return cached_data

        # 非同期でAWS APIを呼び出し
        self.logger.debug(f"{service} AWS API呼び出し開始")
        loop = asyncio.get_event_loop()

        if service == "EC2":
            data = await loop.run_in_executor(
                None, get_ec2_instances, self.region, self.profile
            )
        elif service == "RDS":
            data = await loop.run_in_executor(
                None, get_rds_instances, self.region, self.profile
            )
        elif service == "S3":
            data = await loop.run_in_executor(
                None, get_s3_buckets, self.profile
            )
        elif service == "Lambda":
            data = await loop.run_in_executor(
                None, get_lambda_functions, self.region, self.profile
            )
        else:
            self.logger.warning(f"未対応のサービス: {service}")
            data = pd.DataFrame()

        # キャッシュに保存
        if not data.empty:
            self.cache.set_cached_data(
                service, self.region, self.profile, data
            )
            self.logger.info(
                f"{service} データをキャッシュに保存 ({len(data)}件)"
            )
        else:
            self.logger.warning(f"{service} データが空です")

        return data

    async def fetch_all_data(self) -> Dict[str, pd.DataFrame]:
        """全サービスのデータを並列取得（同時実行数制限付き）"""
        self.logger.info(
            f"並列データ取得開始: {len(self.services)} サービス "
            f"(同時実行数上限: {MAX_CONCURRENT_SERVICES})"
        )

        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SERVICES)

        async def fetch_with_semaphore(service: str) -> pd.DataFrame:
            """セマフォ付きでサービスデータを取得"""
            async with semaphore:
                return await self.fetch_service_data(service)

        # 全サービスを並列実行（同時実行数制限付き）
        tasks = [fetch_with_semaphore(service) for service in self.services]
        results = await asyncio.gather(*tasks)

        # 結果をまとめる
        data_dict = {}
        success_count = 0

        for service, result in zip(self.services, results):
            data_dict[service] = result
            if not result.empty:
                success_count += 1

        self.logger.info(
            f"並列データ取得完了: {success_count}/{len(self.services)} サービス成功"
        )
        return data_dict
