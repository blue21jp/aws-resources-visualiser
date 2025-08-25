#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - 状態管理のテスト"""

# Standard Library
import tempfile
from pathlib import Path
from unittest.mock import patch

# Third Party Library
import pandas as pd

# First Party Library
from app.shared.state_manager import StateManager


class MockSessionState:
    """streamlit.session_stateのモッククラス"""

    def __init__(self):
        self._data = {}

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __getattr__(self, key):
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self._data.get(key)

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestStateManager:
    """StateManager クラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = StateManager()

        # status_dirを一時ディレクトリに設定
        self.state_manager.status_dir = Path(self.temp_dir) / "status"
        self.state_manager.status_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        # 一時ディレクトリをクリーンアップ
        # Standard Library
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ===== アプリケーション状態管理のテスト =====

    def test_ensure_app_state_initialized(self):
        """アプリケーション状態の初期化テスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            self.state_manager._ensure_app_state_initialized()

            assert "app_data" in mock_session
            assert "app_status" in mock_session
            assert "app_error" in mock_session
            assert mock_session["app_status"] == "idle"
            assert mock_session["app_error"] is None

    def test_data_property(self):
        """dataプロパティのテスト"""
        test_data = {"EC2": pd.DataFrame({"Name": ["instance1"]})}
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # データ設定
            self.state_manager.data = test_data
            assert mock_session["app_data"] == test_data

            # データ取得
            retrieved_data = self.state_manager.data
            assert retrieved_data == test_data

    def test_status_property(self):
        """statusプロパティのテスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # ステータス設定
            self.state_manager.status = "loading"
            assert mock_session["app_status"] == "loading"

            # ステータス取得
            status = self.state_manager.status
            assert status == "loading"

    def test_error_message_property(self):
        """error_messageプロパティのテスト"""
        error_msg = "Test error message"
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # エラーメッセージ設定
            self.state_manager.error_message = error_msg
            assert mock_session["app_error"] == error_msg

            # エラーメッセージ取得
            retrieved_error = self.state_manager.error_message
            assert retrieved_error == error_msg

    def test_reset_app_state(self):
        """アプリケーション状態リセットのテスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # 初期状態設定
            self.state_manager.data = {"EC2": pd.DataFrame()}
            self.state_manager.status = "error"
            self.state_manager.error_message = "Some error"

            # リセット実行
            self.state_manager.reset_app_state()

            assert mock_session["app_data"] == {}
            assert mock_session["app_status"] == "idle"
            assert mock_session["app_error"] is None

    def test_has_data(self):
        """has_dataメソッドのテスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # データなしの場合
            assert not self.state_manager.has_data()

            # 空のDataFrameの場合
            self.state_manager.data = {"EC2": pd.DataFrame()}
            assert not self.state_manager.has_data()

            # データありの場合
            self.state_manager.data = {
                "EC2": pd.DataFrame({"Name": ["instance1"]})
            }
            assert self.state_manager.has_data()

    def test_status_check_methods(self):
        """ステータスチェックメソッドのテスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # loading状態
            self.state_manager.status = "loading"
            assert self.state_manager.is_loading()
            assert not self.state_manager.is_completed()
            assert not self.state_manager.is_error()

            # completed状態
            self.state_manager.status = "completed"
            assert not self.state_manager.is_loading()
            assert self.state_manager.is_completed()
            assert not self.state_manager.is_error()

            # error状態
            self.state_manager.status = "error"
            assert not self.state_manager.is_loading()
            assert not self.state_manager.is_completed()
            assert self.state_manager.is_error()

    def test_set_loading(self):
        """set_loadingメソッドのテスト"""
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            self.state_manager.set_loading()

            assert self.state_manager.status == "loading"
            assert self.state_manager.error_message is None

    def test_set_completed(self):
        """set_completedメソッドのテスト"""
        test_data = {"EC2": pd.DataFrame({"Name": ["instance1"]})}
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            self.state_manager.set_completed(test_data)

            assert self.state_manager.status == "completed"
            assert self.state_manager.data == test_data
            assert self.state_manager.error_message is None

    def test_set_error(self):
        """set_errorメソッドのテスト"""
        error_msg = "Test error"
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            self.state_manager.set_error(error_msg)

            assert self.state_manager.status == "error"
            assert self.state_manager.error_message == error_msg

    # ===== 実行状態管理のテスト =====

    def test_get_running_executions(self):
        """get_running_executionsメソッドのテスト"""
        services = ["EC2"]
        region = "us-east-1"
        profile = "test"
        mock_session = MockSessionState()

        with patch("app.shared.state_manager.st.session_state", mock_session):
            # 実行中タスクなしの場合
            assert self.state_manager.get_running_executions() == []

            # 実行中タスクを設定
            mock_session["execution_state"] = {
                "test_key": {
                    "running": True,
                    "services": services,
                    "region": region,
                    "profile": profile,
                }
            }

            # 実行中タスクありの場合
            running_tasks = self.state_manager.get_running_executions()

            assert len(running_tasks) == 1
            assert running_tasks[0]["services"] == services
            assert running_tasks[0]["region"] == region
            assert running_tasks[0]["profile"] == profile

    # ===== ステータスファイル管理のテスト =====

    def test_get_status_file_path(self):
        """_get_status_file_pathメソッドのテスト"""
        services = ["EC2", "RDS"]
        region = "us-east-1"
        profile = "test"

        path = self.state_manager._get_status_file_path(
            services, region, profile
        )

        assert path.parent == self.state_manager.status_dir
        assert path.name == "status_test_us-east-1.json"
        assert path.suffix == ".json"

    def test_get_status_file_path_default_profile(self):
        """_get_status_file_pathメソッドのテスト（デフォルトプロファイル）"""
        services = ["EC2", "RDS"]
        region = "us-east-1"
        profile = None

        path = self.state_manager._get_status_file_path(
            services, region, profile
        )

        assert path.parent == self.state_manager.status_dir
        assert path.name == "status_default_us-east-1.json"
        assert path.suffix == ".json"
