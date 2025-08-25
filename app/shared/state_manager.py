#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - 統合状態管理"""

# Standard Library
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third Party Library
import pandas as pd
import streamlit as st

# First Party Library
from app.shared.config import CACHE_DIR


class StateManager:
    """統合状態管理クラス - アプリ状態、実行状態、ステータスファイルを統合管理"""

    def __init__(self):
        # ステータスファイル管理用
        self.status_dir = Path(CACHE_DIR) / "status"
        self.status_dir.mkdir(parents=True, exist_ok=True)

        # 実行状態管理用
        self.session_key = "execution_state"

    # ===== アプリケーション状態管理 =====

    def _ensure_app_state_initialized(self) -> None:
        """アプリケーション状態の初期化（遅延実行）"""
        if "app_data" not in st.session_state:
            st.session_state.app_data = {}
        if "app_status" not in st.session_state:
            st.session_state.app_status = (
                "idle"  # idle, loading, completed, error
            )
        if "app_error" not in st.session_state:
            st.session_state.app_error = None

    @property
    def data(self) -> Dict[str, pd.DataFrame]:
        """データの取得"""
        self._ensure_app_state_initialized()
        return st.session_state.app_data  # type: ignore[no-any-return]

    @data.setter
    def data(self, value: Dict[str, pd.DataFrame]) -> None:
        """データの設定"""
        self._ensure_app_state_initialized()
        st.session_state.app_data = value

    @property
    def status(self) -> str:
        """ステータスの取得"""
        self._ensure_app_state_initialized()
        return st.session_state.app_status  # type: ignore[no-any-return]

    @status.setter
    def status(self, value: str) -> None:
        """ステータスの設定"""
        self._ensure_app_state_initialized()
        st.session_state.app_status = value

    @property
    def error_message(self) -> Optional[str]:
        """エラーメッセージの取得"""
        self._ensure_app_state_initialized()
        return st.session_state.app_error  # type: ignore[no-any-return]

    @error_message.setter
    def error_message(self, value: Optional[str]) -> None:
        """エラーメッセージの設定"""
        self._ensure_app_state_initialized()
        st.session_state.app_error = value

    def reset_app_state(self) -> None:
        """アプリケーション状態のリセット"""
        self._ensure_app_state_initialized()
        self.data = {}
        self.status = "idle"
        self.error_message = None

    def has_data(self) -> bool:
        """データが存在するかチェック"""
        self._ensure_app_state_initialized()
        return bool(
            self.data and any(not df.empty for df in self.data.values())
        )

    def is_loading(self) -> bool:
        """ローディング中かチェック"""
        self._ensure_app_state_initialized()
        return self.status == "loading"

    def is_completed(self) -> bool:
        """完了状態かチェック"""
        self._ensure_app_state_initialized()
        return self.status == "completed"

    def is_error(self) -> bool:
        """エラー状態かチェック"""
        self._ensure_app_state_initialized()
        return self.status == "error"

    def set_loading(self) -> None:
        """ローディング状態に設定"""
        self._ensure_app_state_initialized()
        self.status = "loading"
        self.error_message = None

    def set_completed(self, data: Dict[str, pd.DataFrame]) -> None:
        """完了状態に設定"""
        self._ensure_app_state_initialized()
        self.data = data
        self.status = "completed"
        self.error_message = None

    def set_error(self, error_message: str) -> None:
        """エラー状態に設定"""
        self._ensure_app_state_initialized()
        self.status = "error"
        self.error_message = error_message

    # ===== 実行状態管理 =====

    def get_running_executions(self) -> List[Dict]:
        """実行中のタスク一覧を取得"""
        if self.session_key not in st.session_state:
            return []

        running_tasks = []
        for key, state in st.session_state[self.session_key].items():
            if state.get("running", False):
                running_tasks.append(
                    {
                        "key": key,
                        "services": state["services"],
                        "region": state["region"],
                        "profile": state["profile"],
                    }
                )

        return running_tasks

    def cleanup_finished_executions(self) -> None:
        """完了したタスクをクリーンアップ"""
        if self.session_key not in st.session_state:
            return

        keys_to_remove = []
        for key, state in st.session_state[self.session_key].items():
            if not state.get("running", False):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del st.session_state[self.session_key][key]

    # ===== ステータスファイル管理 =====

    def _read_status_file_safe(
        self, status_file: Path
    ) -> Optional[Dict[str, Any]]:
        """ステータスファイルを安全に読み込み"""
        if not status_file.exists():
            return None

        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, IOError):
            self._cleanup_status_file(status_file)
            return None

    def _cleanup_status_file(self, status_file: Path) -> None:
        """ステータスファイルをクリーンアップ"""
        try:
            status_file.unlink(missing_ok=True)
        except Exception:
            pass  # ファイル削除エラーは無視

    def _get_status_file_path(
        self, services: List[str], region: str, profile: Optional[str] = None
    ) -> Path:
        """ステータスファイルのパスを生成"""
        # キャッシュファイルと同じ命名パターンを使用
        profile_str = profile or "default"
        return self.status_dir / f"status_{profile_str}_{region}.json"

    def is_status_running(
        self, services: List[str], region: str, profile: Optional[str] = None
    ) -> bool:
        """ステータスファイルで実行中かチェック（簡素化版）"""
        status_file = self._get_status_file_path(services, region, profile)

        try:
            status_data = self._read_status_file_safe(status_file)
            if not status_data:
                return False

            return status_data.get("status") == "running"

        except Exception:
            self._cleanup_status_file(status_file)
            return False

    def start_execution_status(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> None:
        """実行開始ステータスを記録"""
        status_file = self._get_status_file_path(services, region, profile)

        status_data = {
            "status": "running",
            "services": services,
            "region": region,
            "profile": profile,
            "start_time": time.time(),
            "pid": pid,
        }

        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # ファイル書き込みエラーは無視

    def finish_execution_success(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
        result: Optional[Dict] = None,
    ) -> None:
        """実行成功ステータスを記録"""
        status_file = self._get_status_file_path(services, region, profile)

        status_data = {
            "status": "completed",
            "services": services,
            "region": region,
            "profile": profile,
            "end_time": time.time(),
            "result": result,
        }

        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # ファイル書き込みエラーは無視

    def finish_execution_failed(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """実行失敗ステータスを記録"""
        status_file = self._get_status_file_path(services, region, profile)

        status_data = {
            "status": "failed",
            "services": services,
            "region": region,
            "profile": profile,
            "end_time": time.time(),
            "error": error,
        }

        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # ファイル書き込みエラーは無視

    def get_execution_info(
        self, services: List[str], region: str, profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """実行情報を取得（簡素化版）"""
        status_file = self._get_status_file_path(services, region, profile)

        try:
            status_data = self._read_status_file_safe(status_file)
            if not status_data:
                return {"status": "not_found"}

            # ステータスファイルの内容をそのまま返す
            # プロセス生存確認は is_status_running メソッドで行う
            return status_data

        except Exception:
            self._cleanup_status_file(status_file)
            return {"status": "not_found"}

    def clear_all_status_files(self) -> int:
        """すべてのステータスファイルをクリア"""
        cleared_count = 0
        try:
            for status_file in self.status_dir.glob("status_*.json"):
                status_file.unlink(missing_ok=True)
                cleared_count += 1
        except Exception as e:
            logging.warning(
                f"ステータスファイルのクリア中にエラーが発生しました: {e}"
            )

        return cleared_count


# シングルトンインスタンス
_state_manager_instance = None


def get_state_manager() -> StateManager:
    """StateManagerのシングルトンインスタンスを取得"""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
