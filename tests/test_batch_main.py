#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""バッチ処理メインモジュールのテスト"""

# Standard Library
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Third Party Library
import pandas as pd
import pytest
from click.testing import CliRunner

# First Party Library
from app.batch.main import async_main, execute_data_fetch, main
from app.shared.state_manager import StateManager


class TestBatchMain:
    """バッチ処理メインのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.runner = CliRunner()

    def test_help_option(self):
        """ヘルプオプションのテスト"""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--services" in result.output
        assert "--region" in result.output
        assert "--profile" in result.output

    def test_main_invalid_service(self):
        """無効なサービス指定のテスト"""
        result = self.runner.invoke(
            main,
            [
                "--services",
                "INVALID_SERVICE",
                "--region",
                "us-east-1",
                "--profile",
                "sandbox",
            ],
        )

        # Clickが引数検証でエラーを出すことを確認
        assert result.exit_code != 0

    @patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-west-2"})
    def test_main_ecs_environment_region_detection(self):
        """ECS環境でのリージョン検出テスト"""
        # 実際の実行はせず、環境変数の設定のみテスト
        # Standard Library
        import os

        assert os.environ.get("AWS_DEFAULT_REGION") == "us-west-2"

    @pytest.mark.parametrize(
        "services",
        [
            ["EC2"],
            ["EC2", "RDS"],
            ["S3", "Lambda"],
        ],
    )
    def test_service_validation(self, services):
        """サービス名の検証テスト"""
        # First Party Library
        from app.shared.config import SUPPORTED_SERVICES

        # 指定されたサービスがサポートされていることを確認
        for service in services:
            assert service in SUPPORTED_SERVICES

    @patch("app.batch.main.get_state_manager")
    @patch("app.batch.main.execute_data_fetch")
    @patch("app.batch.main.setup_logging")
    @patch("builtins.print")
    def test_async_main_success(
        self,
        mock_print,
        mock_setup_logging,
        mock_execute_data_fetch,
        mock_get_state_manager,
    ):
        """async_main成功時のテスト"""
        # モックの設定
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_state_manager = MagicMock()
        mock_state_manager.is_status_running.return_value = False
        mock_get_state_manager.return_value = mock_state_manager

        mock_execute_data_fetch.return_value = None

        # テスト実行
        asyncio.run(async_main(["EC2"], "us-east-1", "sandbox", False, False))

        # 検証
        mock_setup_logging.assert_called_once()
        mock_state_manager.is_status_running.assert_called_once_with(
            ["EC2"], "us-east-1", "sandbox"
        )
        mock_state_manager.start_execution_status.assert_called_once()
        mock_execute_data_fetch.assert_called_once()

    @patch("app.batch.main.get_state_manager")
    @patch("app.batch.main.execute_data_fetch")
    @patch("app.batch.main.setup_logging")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_async_main_exception_handling(
        self,
        mock_exit,
        mock_print,
        mock_setup_logging,
        mock_execute_data_fetch,
        mock_get_state_manager,
    ):
        """例外処理のテスト"""
        # モックの設定
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_state_manager = MagicMock()
        mock_state_manager.is_status_running.return_value = False
        mock_get_state_manager.return_value = mock_state_manager

        mock_execute_data_fetch.side_effect = Exception("テストエラー")

        # テスト実行
        asyncio.run(async_main(["EC2"], "us-east-1", "sandbox", False, False))

        # 検証
        mock_exit.assert_called_once_with(1)
        mock_state_manager.finish_execution_failed.assert_called_once()
        mock_print.assert_called_once()
        printed_output = mock_print.call_args[0][0]
        result = json.loads(printed_output)
        assert result["success"] is False
        assert "テストエラー" in result["error"]

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.batch.main.get_state_manager")
    @patch("app.batch.main.execute_data_fetch")
    @patch("app.batch.main.setup_logging")
    def test_async_main_region_from_default(
        self,
        mock_setup_logging,
        mock_execute_data_fetch,
        mock_get_state_manager,
    ):
        """リージョンがデフォルト値から取得されるテスト"""
        # モックの設定
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_state_manager = MagicMock()
        mock_state_manager.is_status_running.return_value = False
        mock_get_state_manager.return_value = mock_state_manager

        # DEFAULT_REGIONの値を取得
        # First Party Library
        from app.shared.config import DEFAULT_REGION

        # テスト実行（DEFAULT_REGIONを直接渡す）
        asyncio.run(
            async_main(["EC2"], DEFAULT_REGION, "sandbox", False, False)
        )

        # 検証：DEFAULT_REGIONが使用されることを確認
        mock_execute_data_fetch.assert_called_once()
        call_args = mock_execute_data_fetch.call_args[0]
        assert call_args[2] == DEFAULT_REGION  # regionパラメータ


class TestExecuteDataFetch:
    """データ取得実行のテストクラス"""

    @patch("app.batch.main.DataFetcher")
    @patch("builtins.print")
    def test_execute_data_fetch_success(
        self, mock_print, mock_data_fetcher_class
    ):
        """データ取得成功のテスト"""
        # モックの設定
        mock_fetcher = MagicMock()
        mock_data_fetcher_class.return_value = mock_fetcher

        # テストデータ
        test_results = {
            "EC2": pd.DataFrame([{"id": "i-123", "name": "test"}]),
            "RDS": pd.DataFrame(),  # 空のDataFrame
        }
        mock_fetcher.fetch_all_data = AsyncMock(return_value=test_results)

        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        # テスト実行
        asyncio.run(
            execute_data_fetch(
                ["EC2", "RDS"],
                mock_state_manager,
                "us-east-1",
                "sandbox",
                False,
                False,
                mock_logger,
            )
        )

        # 検証
        mock_fetcher.fetch_all_data.assert_called_once()
        mock_state_manager.finish_execution_success.assert_called_once()
        mock_print.assert_called_once()

        # 出力結果の検証
        printed_output = mock_print.call_args[0][0]
        result = json.loads(printed_output)
        assert result["success"] is True
        assert result["success_count"] == 1  # EC2のみ成功
        assert result["total_count"] == 2

    @patch("app.batch.main.DataFetcher")
    def test_execute_data_fetch_with_clear_cache(
        self, mock_data_fetcher_class
    ):
        """キャッシュクリア付きデータ取得のテスト"""
        # モックの設定
        mock_fetcher = MagicMock()
        mock_data_fetcher_class.return_value = mock_fetcher
        mock_fetcher.fetch_all_data = AsyncMock(
            return_value={"EC2": pd.DataFrame()}
        )

        mock_state_manager = MagicMock()
        mock_logger = MagicMock()

        # テスト実行
        asyncio.run(
            execute_data_fetch(
                ["EC2"],
                mock_state_manager,
                "us-east-1",
                "sandbox",
                True,
                False,
                mock_logger,
            )
        )

        # 検証
        mock_fetcher.clear_cache.assert_called_once()
        mock_fetcher.fetch_all_data.assert_called_once()


class TestBatchMainIntegration:
    """バッチ処理の統合テスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.runner = CliRunner()

    def test_help_and_version_info(self):
        """ヘルプとバージョン情報のテスト"""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert (
            "AWS Resource Visualizer" in result.output
            or "Usage:" in result.output
        )

    def test_command_structure(self):
        """コマンド構造の基本テスト"""
        # コマンドが正しくインポートできることを確認
        # First Party Library
        from app.batch.main import main

        assert main is not None
        assert callable(main)


class TestStatusFileNaming:
    """ステータスファイル命名規則のテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = StateManager()
        self.state_manager.status_dir = Path(self.temp_dir) / "status"
        self.state_manager.status_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        # Standard Library
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_status_file_naming_with_profile(self):
        """プロファイル指定時のステータスファイル命名テスト"""
        services = ["EC2", "RDS"]
        region = "us-east-1"
        profile = "sandbox"

        path = self.state_manager._get_status_file_path(
            services, region, profile
        )

        expected_name = "status_sandbox_us-east-1.json"
        assert path.name == expected_name

    def test_status_file_naming_without_profile(self):
        """プロファイル未指定時のステータスファイル命名テスト（ECS環境想定）"""
        services = ["EC2", "RDS"]
        region = "us-east-1"
        profile = None

        path = self.state_manager._get_status_file_path(
            services, region, profile
        )

        expected_name = "status_default_us-east-1.json"
        assert path.name == expected_name

    def test_status_file_naming_different_regions(self):
        """異なるリージョンでのステータスファイル命名テスト"""
        services = ["EC2"]
        profile = "sandbox"

        # us-east-1
        path1 = self.state_manager._get_status_file_path(
            services, "us-east-1", profile
        )
        # ap-northeast-1
        path2 = self.state_manager._get_status_file_path(
            services, "ap-northeast-1", profile
        )

        assert path1.name == "status_sandbox_us-east-1.json"
        assert path2.name == "status_sandbox_ap-northeast-1.json"
        assert path1.name != path2.name

    def test_status_file_naming_different_profiles(self):
        """異なるプロファイルでのステータスファイル命名テスト"""
        services = ["EC2"]
        region = "us-east-1"

        # sandboxプロファイル
        path1 = self.state_manager._get_status_file_path(
            services, region, "sandbox"
        )
        # productionプロファイル
        path2 = self.state_manager._get_status_file_path(
            services, region, "production"
        )

        assert path1.name == "status_sandbox_us-east-1.json"
        assert path2.name == "status_production_us-east-1.json"
        assert path1.name != path2.name

    def test_status_file_naming_same_services_different_order(self):
        """同じサービスの異なる順序でのステータスファイル命名テスト"""
        region = "us-east-1"
        profile = "sandbox"

        # サービスの順序が異なっても同じファイル名になることを確認
        path1 = self.state_manager._get_status_file_path(
            ["EC2", "RDS"], region, profile
        )
        path2 = self.state_manager._get_status_file_path(
            ["RDS", "EC2"], region, profile
        )

        # 新しい命名規則では、サービスに関係なく同じファイル名
        assert path1.name == path2.name
        assert path1.name == "status_sandbox_us-east-1.json"
