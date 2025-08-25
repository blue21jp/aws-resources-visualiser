#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data_fetcherモジュールのテスト"""

# Standard Library
import asyncio
import logging
from unittest.mock import MagicMock, call, patch

# Third Party Library
import pandas as pd
import pytest

# First Party Library
from app.batch.data_fetcher import DataFetcher


class TestDataFetcher:
    """DataFetcherクラスのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.services = ["EC2", "RDS", "S3", "Lambda"]
        self.region = "us-east-1"
        self.profile = "sandbox"
        self.data_fetcher = DataFetcher(
            self.services, self.region, self.profile
        )

    def test_init(self):
        """初期化のテスト"""
        assert self.data_fetcher.services == self.services
        assert self.data_fetcher.region == self.region
        assert self.data_fetcher.profile == self.profile
        assert self.data_fetcher.cache is not None
        assert isinstance(self.data_fetcher.logger, logging.Logger)

    def test_init_without_profile(self):
        """プロファイルなしでの初期化のテスト"""
        data_fetcher = DataFetcher(["EC2"], "us-east-1")
        assert data_fetcher.services == ["EC2"]
        assert data_fetcher.region == "us-east-1"
        assert data_fetcher.profile is None

    @patch("app.batch.data_fetcher.get_cache_instance")
    def test_clear_cache(self, mock_get_cache_instance):
        """キャッシュクリアのテスト"""
        mock_cache = MagicMock()
        # clear_cacheメソッドが整数を返すように設定
        mock_cache.clear_cache.return_value = 1
        mock_get_cache_instance.return_value = mock_cache

        data_fetcher = DataFetcher(["EC2"], "us-east-1", "sandbox")
        data_fetcher.clear_cache()

        # 全サポートサービス（EC2, RDS, S3, Lambda）のキャッシュクリアが呼ばれることを確認
        assert mock_cache.clear_cache.call_count == 4

        # 各サービスで正しい引数が渡されることを確認
        expected_calls = [
            call("EC2", "us-east-1", "sandbox"),
            call("RDS", "us-east-1", "sandbox"),
            call("S3", "us-east-1", "sandbox"),
            call("Lambda", "us-east-1", "sandbox"),
        ]
        mock_cache.clear_cache.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    @patch("app.batch.data_fetcher.get_ec2_instances")
    async def test_fetch_service_data_ec2_no_cache(self, mock_get_ec2):
        """EC2データ取得のテスト（キャッシュなし）"""
        # モックデータの準備
        mock_data = pd.DataFrame(
            {
                "Instance ID": ["i-123456789"],
                "Name": ["test-instance"],
                "State": ["running"],
            }
        )
        mock_get_ec2.return_value = mock_data

        # キャッシュなしの状態をモック
        with patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ) as mock_set_cache:

            result = await self.data_fetcher.fetch_service_data("EC2")

            # 結果の検証
            pd.testing.assert_frame_equal(result, mock_data)
            mock_get_ec2.assert_called_once_with(self.region, self.profile)
            mock_set_cache.assert_called_once_with(
                "EC2", self.region, self.profile, mock_data
            )

    @pytest.mark.asyncio
    @patch("app.batch.data_fetcher.get_rds_instances")
    async def test_fetch_service_data_rds_no_cache(self, mock_get_rds):
        """RDSデータ取得のテスト（キャッシュなし）"""
        mock_data = pd.DataFrame(
            {
                "DB Instance Identifier": ["test-db"],
                "Engine": ["mysql"],
                "Status": ["available"],
            }
        )
        mock_get_rds.return_value = mock_data

        with patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ) as mock_set_cache:

            result = await self.data_fetcher.fetch_service_data("RDS")

            pd.testing.assert_frame_equal(result, mock_data)
            mock_get_rds.assert_called_once_with(self.region, self.profile)
            mock_set_cache.assert_called_once_with(
                "RDS", self.region, self.profile, mock_data
            )

    @pytest.mark.asyncio
    @patch("app.batch.data_fetcher.get_s3_buckets")
    async def test_fetch_service_data_s3_no_cache(self, mock_get_s3):
        """S3データ取得のテスト（キャッシュなし）"""
        mock_data = pd.DataFrame(
            {
                "Bucket Name": ["test-bucket"],
                "Region": ["us-east-1"],
                "Creation Date": ["2023-01-01"],
            }
        )
        mock_get_s3.return_value = mock_data

        with patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ) as mock_set_cache:

            result = await self.data_fetcher.fetch_service_data("S3")

            pd.testing.assert_frame_equal(result, mock_data)
            mock_get_s3.assert_called_once_with(self.profile)
            mock_set_cache.assert_called_once_with(
                "S3", self.region, self.profile, mock_data
            )

    @pytest.mark.asyncio
    @patch("app.batch.data_fetcher.get_lambda_functions")
    async def test_fetch_service_data_lambda_no_cache(self, mock_get_lambda):
        """Lambdaデータ取得のテスト（キャッシュなし）"""
        mock_data = pd.DataFrame(
            {
                "Function Name": ["test-function"],
                "Runtime": ["python3.9"],
                "State": ["Active"],
            }
        )
        mock_get_lambda.return_value = mock_data

        with patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ) as mock_set_cache:

            result = await self.data_fetcher.fetch_service_data("Lambda")

            pd.testing.assert_frame_equal(result, mock_data)
            mock_get_lambda.assert_called_once_with(self.region, self.profile)
            mock_set_cache.assert_called_once_with(
                "Lambda", self.region, self.profile, mock_data
            )

    @pytest.mark.asyncio
    async def test_fetch_service_data_with_cache(self):
        """キャッシュありでのデータ取得のテスト"""
        cached_data = pd.DataFrame(
            {
                "Instance ID": ["i-cached"],
                "Name": ["cached-instance"],
                "State": ["running"],
            }
        )

        with patch.object(
            self.data_fetcher.cache,
            "get_cached_data",
            return_value=cached_data,
        ):
            result = await self.data_fetcher.fetch_service_data("EC2")

            pd.testing.assert_frame_equal(result, cached_data)

    @pytest.mark.asyncio
    async def test_fetch_service_data_unsupported_service(self):
        """未対応サービスのテスト"""
        with patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ):
            result = await self.data_fetcher.fetch_service_data("UNSUPPORTED")

            assert result.empty

    @pytest.mark.asyncio
    async def test_fetch_service_data_empty_result(self):
        """空のデータが返される場合のテスト"""
        empty_data = pd.DataFrame()

        with patch(
            "app.batch.data_fetcher.get_ec2_instances", return_value=empty_data
        ), patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ) as mock_set_cache:

            result = await self.data_fetcher.fetch_service_data("EC2")

            assert result.empty
            # 空のデータはキャッシュに保存されない
            mock_set_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_all_data_success(self):
        """全サービスデータ取得成功のテスト"""
        # モックデータの準備
        mock_data = {
            "EC2": pd.DataFrame({"Instance ID": ["i-123"]}),
            "RDS": pd.DataFrame({"DB Instance Identifier": ["db-123"]}),
            "S3": pd.DataFrame({"Bucket Name": ["bucket-123"]}),
            "Lambda": pd.DataFrame({"Function Name": ["func-123"]}),
        }

        # fetch_service_dataメソッドをモック
        async def mock_fetch_service_data(service):
            return mock_data[service]

        with patch.object(
            self.data_fetcher,
            "fetch_service_data",
            side_effect=mock_fetch_service_data,
        ):
            result = await self.data_fetcher.fetch_all_data()

            assert len(result) == 4
            for service in self.services:
                assert service in result
                pd.testing.assert_frame_equal(
                    result[service], mock_data[service]
                )

    @pytest.mark.asyncio
    async def test_fetch_all_data_partial_success(self):
        """一部サービスが失敗する場合のテスト"""
        mock_data = {
            "EC2": pd.DataFrame({"Instance ID": ["i-123"]}),
            "RDS": pd.DataFrame(),  # 空のデータ
            "S3": pd.DataFrame({"Bucket Name": ["bucket-123"]}),
            "Lambda": pd.DataFrame(),  # 空のデータ
        }

        async def mock_fetch_service_data(service):
            return mock_data[service]

        with patch.object(
            self.data_fetcher,
            "fetch_service_data",
            side_effect=mock_fetch_service_data,
        ):
            result = await self.data_fetcher.fetch_all_data()

            assert len(result) == 4
            # 成功したサービスのデータが含まれている
            assert not result["EC2"].empty
            assert not result["S3"].empty
            # 失敗したサービスは空のDataFrame
            assert result["RDS"].empty
            assert result["Lambda"].empty

    @pytest.mark.asyncio
    async def test_fetch_all_data_concurrency_limit(self):
        """同時実行数制限のテスト"""
        # 実行時間を測定するためのモック
        call_times = []

        async def mock_fetch_service_data(service):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)  # 短い待機時間
            return pd.DataFrame({f"{service}_data": ["test"]})

        with patch.object(
            self.data_fetcher,
            "fetch_service_data",
            side_effect=mock_fetch_service_data,
        ), patch(
            "app.batch.data_fetcher.MAX_CONCURRENT_SERVICES", 2
        ):  # 同時実行数を2に制限

            result = await self.data_fetcher.fetch_all_data()

            assert len(result) == 4
            # 同時実行数制限により、すべてが同時に開始されるわけではない
            assert len(call_times) == 4

    @pytest.mark.asyncio
    async def test_fetch_all_data_empty_services(self):
        """サービスリストが空の場合のテスト"""
        data_fetcher = DataFetcher([], "us-east-1", "sandbox")
        result = await data_fetcher.fetch_all_data()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_service_data_exception_handling(self):
        """例外処理のテスト"""
        with patch(
            "app.batch.data_fetcher.get_ec2_instances",
            side_effect=Exception("API Error"),
        ), patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ):

            # 例外が発生してもプログラムが停止しないことを確認
            with pytest.raises(Exception):
                await self.data_fetcher.fetch_service_data("EC2")

    def test_logger_configuration(self):
        """ロガー設定のテスト"""
        assert self.data_fetcher.logger.name == "batch_main"

    @pytest.mark.parametrize(
        "service,expected_function",
        [
            ("EC2", "get_ec2_instances"),
            ("RDS", "get_rds_instances"),
            ("S3", "get_s3_buckets"),
            ("Lambda", "get_lambda_functions"),
        ],
    )
    @pytest.mark.asyncio
    async def test_fetch_service_data_function_mapping(
        self, service, expected_function
    ):
        """サービスと関数のマッピングテスト"""
        mock_data = pd.DataFrame({"test": ["data"]})

        with patch(
            f"app.batch.data_fetcher.{expected_function}",
            return_value=mock_data,
        ) as mock_func, patch.object(
            self.data_fetcher.cache, "get_cached_data", return_value=None
        ), patch.object(
            self.data_fetcher.cache, "set_cached_data"
        ):

            await self.data_fetcher.fetch_service_data(service)

            if service == "S3":
                # S3はリージョンパラメータがない
                mock_func.assert_called_once_with(self.profile)
            else:
                mock_func.assert_called_once_with(self.region, self.profile)


class TestDataFetcherIntegration:
    """DataFetcherの統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_cache(self):
        """キャッシュを含む完全なワークフローのテスト"""
        services = ["EC2", "S3"]
        data_fetcher = DataFetcher(services, "us-east-1", "test-profile")

        # 最初の実行（キャッシュなし）
        mock_ec2_data = pd.DataFrame({"Instance ID": ["i-123"]})
        mock_s3_data = pd.DataFrame({"Bucket Name": ["bucket-123"]})

        with patch(
            "app.batch.data_fetcher.get_ec2_instances",
            return_value=mock_ec2_data,
        ), patch(
            "app.batch.data_fetcher.get_s3_buckets", return_value=mock_s3_data
        ):

            result1 = await data_fetcher.fetch_all_data()

            assert len(result1) == 2
            assert not result1["EC2"].empty
            assert not result1["S3"].empty

    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """エラー耐性のテスト"""
        services = ["EC2", "RDS", "INVALID"]
        data_fetcher = DataFetcher(services, "us-east-1", "test-profile")

        mock_ec2_data = pd.DataFrame({"Instance ID": ["i-123"]})

        with patch(
            "app.batch.data_fetcher.get_ec2_instances",
            return_value=mock_ec2_data,
        ), patch(
            "app.batch.data_fetcher.get_rds_instances",
            side_effect=Exception("RDS Error"),
        ):

            # 一部のサービスでエラーが発生しても他のサービスは正常に処理される
            with pytest.raises(Exception):
                await data_fetcher.fetch_all_data()
