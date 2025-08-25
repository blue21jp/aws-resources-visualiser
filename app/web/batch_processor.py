#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - バッチ処理統合管理"""

# Standard Library
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Third Party Library
import pandas as pd

# First Party Library
from app.shared.cache_manager import get_cache_instance
from app.shared.config import (
    BATCH_RUN_TYPE,
    get_effective_region,
    should_use_profile_in_command,
    should_use_region_in_command,
)
from app.shared.state_manager import get_state_manager


class BatchProcessor:
    """バッチ処理の統合管理クラス"""

    def __init__(self):
        self.batch_module = "app.batch.main"
        self.state_manager = get_state_manager()
        self.cache = get_cache_instance()
        self.logger = logging.getLogger(__name__)

    # ===== 統一処理メソッド =====

    def handle_execution(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
        clear_cache: bool = False,
        force: bool = False,
    ) -> str:
        """バッチ実行の統一処理

        Args:
            services: 取得するサービスリスト
            region: AWSリージョン
            profile: AWSプロファイル
            clear_cache: キャッシュクリアフラグ
            force: 強制実行フラグ（WebUIからは常にFalse）

        Returns:
            str: 実行結果のステータス ('loading', 'completed', 'error', 'started')
        """
        if not self.is_batch_available():
            self.state_manager.set_error("バッチスクリプトが見つかりません")
            return "error"

        # 統合ステータスチェック（1回のチェックで全て判定）
        execution_info = self._get_comprehensive_status(
            services, region, profile
        )

        if execution_info["is_running"]:
            # forceフラグがFalseの場合（WebUIからの呼び出し）はエラーとして扱う
            if not force:
                self.state_manager.set_error(
                    "同じ条件でバッチが実行中です。処理が完了するまでお待ちください。"
                )
                return "error"
            # forceフラグがTrueの場合は処理を続行（バッチからの--forceオプション）

        elif execution_info["status"] == "completed":
            # キャッシュクリアが指定されている場合は新しいバッチを開始
            if clear_cache:
                return self._start_new_batch(
                    services, region, profile, clear_cache, force
                )

            # キャッシュからデータを読み込み
            if self._load_data_from_cache(services, region, profile):
                self.state_manager.set_completed(self.state_manager.data)
                return "completed"
            else:
                self.state_manager.set_error(
                    "キャッシュデータの読み込みに失敗しました"
                )
                return "error"

        elif execution_info["status"] == "failed":
            error_msg = execution_info.get("error", "不明なエラー")
            self.state_manager.set_error(
                f"前回のバッチ実行でエラーが発生: {error_msg}"
            )
            # 新しいバッチを開始するため、処理を続行

        # 新しいバッチを開始
        return self._start_new_batch(
            services, region, profile, clear_cache, force
        )

    def _get_comprehensive_status(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        """統合ステータスチェック（1回のチェックで全て判定）"""
        effective_region = get_effective_region(region)

        # 実行中のタスクをクリーンアップ
        self.cleanup_finished_tasks()

        # ステータス情報を取得
        execution_status = self.state_manager.get_execution_info(
            services, effective_region, profile
        )

        status = execution_status.get("status", "not_found")

        return {
            "status": status,
            "is_running": status == "running",
            "error": execution_status.get("error"),
            "result": execution_status.get("result"),
        }

    def _start_new_batch(
        self,
        services: List[str],
        region: str,
        profile: Optional[str],
        clear_cache: bool,
        force: bool,
    ) -> str:
        """新しいバッチを開始"""
        # キャッシュクリアが指定された場合、AppStateをリセット
        if clear_cache:
            self.state_manager.reset_app_state()

        # バッチを非同期で開始
        result = self.start_data_fetch(
            services=services,
            region=region,
            profile=profile,
            clear_cache=clear_cache,
            force=force,
        )

        if result.get("success", False):
            self.state_manager.set_loading()
            return "started"
        else:
            error_msg = result.get("error", "不明なエラー")
            self.state_manager.set_error(f"バッチ開始エラー: {error_msg}")
            return "error"

    def _load_data_from_cache(
        self,
        services: List[str],
        region: str,
        profile: Optional[str],
    ) -> bool:
        """キャッシュからデータを読み込み"""
        # ECS環境では実際のリージョンは環境変数から取得されるため、
        # キャッシュキーも環境変数のリージョンを使用
        cache_region = get_effective_region(region)

        data = {}
        for service in services:
            cached_data = self.cache.get_cached_data(
                service, cache_region, profile
            )
            if cached_data is not None:
                data[service] = cached_data
            else:
                data[service] = pd.DataFrame()

        # キャッシュサイズをチェック
        cache_size = self.cache.get_cache_size()
        if cache_size["file_count"] > 0:
            self.state_manager.data = data
            return True

        return False

    # ===== バッチ実行管理 =====

    def is_batch_available(self) -> bool:
        """バッチモジュールが利用可能かチェック"""
        try:
            # First Party Library
            import app.batch.main  # noqa: F401

            return True
        except ImportError:
            return False

    def start_data_fetch(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
        clear_cache: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """バッチでデータ取得を非同期開始"""
        try:
            # コマンドを構築
            cmd = self._build_batch_command(
                services, region, profile, clear_cache, force
            )

            # バッチを非同期で実行（ステータス管理はバッチ側で行う）
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            return {"success": True, "pid": process.pid}

        except Exception as e:
            # エラー時もバッチ側でステータス管理するため、WEB側では何もしない
            return {"success": False, "error": str(e)}

    def _build_batch_command(
        self,
        services: List[str],
        region: str,
        profile: Optional[str],
        clear_cache: bool,
        force: bool,
    ) -> List[str]:
        """バッチコマンドを構築"""
        if BATCH_RUN_TYPE == "poetry":
            cmd = ["poetry", "run", "python", "-m", self.batch_module]
        else:
            cmd = [sys.executable, "-m", self.batch_module]

        # サービス指定
        for service in services:
            cmd.extend(["--services", service])

        # リージョン指定（Poetry・Docker環境）
        if should_use_region_in_command():
            cmd.extend(["--region", region])

        # プロファイル指定（Poetry・Docker環境）
        if should_use_profile_in_command(profile):
            cmd.extend(["--profile", profile])  # type: ignore[list-item]

        # オプション
        if clear_cache:
            cmd.append("--clear-cache")

        if force:
            cmd.append("--force")

        # デバッグ用：コマンドをログ出力
        self.logger.debug(f"バッチコマンド: {' '.join(cmd)}")

        return cmd

    def get_execution_status(
        self,
        services: List[str],
        region: str,
        profile: Optional[str] = None,
    ) -> Dict:
        """実行ステータスを取得"""
        if not self.is_batch_available():
            return {"status": "unavailable"}

        effective_region = get_effective_region(region)
        return self.state_manager.get_execution_info(
            services, effective_region, profile
        )

    def cleanup_finished_tasks(self) -> None:
        """完了したタスクをクリーンアップ"""
        self.state_manager.cleanup_finished_executions()


# シングルトンインスタンス
_batch_processor_instance = None


def get_batch_processor() -> BatchProcessor:
    """BatchProcessorのシングルトンインスタンスを取得"""
    global _batch_processor_instance
    if _batch_processor_instance is None:
        _batch_processor_instance = BatchProcessor()
    return _batch_processor_instance
