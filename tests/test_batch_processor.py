#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - バッチプロセッサのテスト"""

# Standard Library
from unittest.mock import MagicMock, patch

# First Party Library
from app.web.batch_processor import BatchProcessor


class TestBatchProcessor:
    """BatchProcessor クラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        with patch("app.web.batch_processor.get_state_manager"), patch(
            "app.web.batch_processor.get_cache_instance"
        ):
            self.batch_processor = BatchProcessor()

    def test_init(self):
        """初期化のテスト"""
        with patch(
            "app.web.batch_processor.get_state_manager"
        ) as mock_state_manager, patch(
            "app.web.batch_processor.get_cache_instance"
        ) as mock_cache:

            processor = BatchProcessor()

            assert processor.batch_module == "app.batch.main"
            mock_state_manager.assert_called_once()
            mock_cache.assert_called_once()

    def test_handle_execution_batch_not_available(self):
        """バッチが利用できない場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=False
        ):
            result = self.batch_processor.handle_execution(
                services, region, profile
            )

            assert result == "error"
            self.batch_processor.state_manager.set_error.assert_called_once_with(  # type: ignore
                "バッチスクリプトが見つかりません"
            )

    def test_handle_execution_running_status(self):
        """実行中ステータスの場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "running", "is_running": True},
        ):

            result = self.batch_processor.handle_execution(
                services, region, profile
            )

            assert result == "error"
            self.batch_processor.state_manager.set_error.assert_called_once_with(  # type: ignore
                "同じ条件でバッチが実行中です。処理が完了するまでお待ちください。"
            )

    def test_handle_execution_running_status_with_force(self):
        """実行中ステータスでforce=Trueの場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "running", "is_running": True},
        ), patch.object(
            self.batch_processor, "_start_new_batch", return_value="started"
        ):

            result = self.batch_processor.handle_execution(
                services, region, profile, force=True
            )

            assert result == "started"
            self.batch_processor._start_new_batch.assert_called_once_with(  # type: ignore
                services, region, profile, False, True
            )

    def test_handle_execution_completed_status_with_cache(self):
        """完了ステータスでキャッシュありの場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "completed", "is_running": False},
        ), patch.object(
            self.batch_processor, "_load_data_from_cache", return_value=True
        ):

            result = self.batch_processor.handle_execution(
                services, region, profile, clear_cache=False
            )

            assert result == "completed"
            self.batch_processor.state_manager.set_completed.assert_called_once()  # type: ignore

    def test_handle_execution_completed_status_cache_failed(self):
        """完了ステータスでキャッシュ読み込み失敗の場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "completed", "is_running": False},
        ), patch.object(
            self.batch_processor, "_load_data_from_cache", return_value=False
        ):

            result = self.batch_processor.handle_execution(
                services, region, profile, clear_cache=False
            )

            assert result == "error"
            self.batch_processor.state_manager.set_error.assert_called_once_with(  # type: ignore
                "キャッシュデータの読み込みに失敗しました"
            )

    def test_handle_execution_completed_with_clear_cache(self):
        """完了ステータスでキャッシュクリア指定の場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor, "cleanup_finished_tasks"
        ), patch.object(
            self.batch_processor,
            "get_execution_status",
            return_value={"status": "completed"},
        ), patch.object(
            self.batch_processor, "_start_new_batch", return_value="started"
        ):

            result = self.batch_processor.handle_execution(
                services, region, profile, clear_cache=True
            )

            assert result == "started"
            self.batch_processor._start_new_batch.assert_called_once_with(  # type: ignore
                services, region, profile, True, False
            )

    def test_handle_execution_failed_status(self):
        """失敗ステータスの場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"
        error_msg = "Test error message"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor, "cleanup_finished_tasks"
        ), patch.object(
            self.batch_processor,
            "get_execution_status",
            return_value={"status": "failed", "error": error_msg},
        ):

            self.batch_processor.handle_execution(services, region, profile)

            # 失敗ステータスの場合の処理を確認（実装に依存）
            # 実際の実装では新しいバッチを開始するか、エラーを設定するかを確認

    def test_handle_execution_unknown_status(self):
        """不明なステータスの場合のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor, "cleanup_finished_tasks"
        ), patch.object(
            self.batch_processor,
            "get_execution_status",
            return_value={"status": "unknown"},
        ):

            # 不明なステータスの場合の処理をテスト
            # 実装に応じて適切なアサーションを追加
            self.batch_processor.handle_execution(services, region, profile)

            # 実装に応じて結果を確認

    def test_handle_execution_method_call_order(self):
        """メソッド呼び出し順序のテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        call_order = []

        def track_call(method_name):
            def wrapper(*args, **kwargs):
                call_order.append(method_name)
                if method_name == "is_batch_available":
                    return True
                elif method_name == "_get_comprehensive_status":
                    return {"status": "running", "is_running": True}
                return MagicMock()

            return wrapper

        with patch.object(
            self.batch_processor,
            "is_batch_available",
            side_effect=track_call("is_batch_available"),
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            side_effect=track_call("_get_comprehensive_status"),
        ):

            self.batch_processor.handle_execution(services, region, profile)

            expected_order = [
                "is_batch_available",
                "_get_comprehensive_status",
            ]
            assert call_order == expected_order

    def test_handle_execution_parameters(self):
        """パラメータ渡しのテスト"""
        services = ["EC2", "RDS"]
        region = "ap-northeast-1"
        profile = "production"
        clear_cache = True

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "completed", "is_running": False},
        ) as mock_get_status, patch.object(
            self.batch_processor, "_start_new_batch", return_value="started"
        ) as mock_start_batch:

            self.batch_processor.handle_execution(
                services, region, profile, clear_cache
            )

            # パラメータが正しく渡されることを確認
            mock_get_status.assert_called_once_with(services, region, profile)
            mock_start_batch.assert_called_once_with(
                services, region, profile, clear_cache, False
            )

    def test_get_comprehensive_status(self):
        """_get_comprehensive_statusメソッドのテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "sandbox"

        with patch.object(
            self.batch_processor, "cleanup_finished_tasks"
        ), patch.object(
            self.batch_processor.state_manager,
            "get_execution_info",
            return_value={"status": "running", "pid": 12345},
        ), patch(
            "app.web.batch_processor.get_effective_region",
            return_value="us-east-1",
        ):

            result = self.batch_processor._get_comprehensive_status(
                services, region, profile
            )

            assert result["status"] == "running"
            assert result["is_running"] is True
            assert result["error"] is None

    def test_handle_execution_default_parameters(self):
        """デフォルトパラメータのテスト"""
        services = ["S3"]
        region = "us-west-2"

        with patch.object(
            self.batch_processor, "is_batch_available", return_value=True
        ), patch.object(
            self.batch_processor,
            "_get_comprehensive_status",
            return_value={"status": "running", "is_running": True},
        ) as mock_get_status:

            self.batch_processor.handle_execution(services, region)

            # デフォルトパラメータで呼ばれることを確認
            mock_get_status.assert_called_once_with(services, region, None)
