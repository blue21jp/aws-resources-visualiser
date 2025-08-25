#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - サイドバーUI管理"""

# Standard Library
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

# Third Party Library
import streamlit as st

# Local Library
from ..shared.config import (
    AVAILABLE_PROFILES,
    CACHE_TTL,
    DEFAULT_PROFILE,
    DEFAULT_REGION,
    DEFAULT_SERVICES,
    STREAMLIT_CONFIG,
    SUPPORTED_REGIONS,
    SUPPORTED_SERVICES,
)
from .pagination import reset_pagination


class SidebarUI:
    """サイドバーUI管理クラス"""

    def __init__(self):
        self.running_on_ecs = self._is_running_on_ecs()

    @staticmethod
    def _is_running_on_ecs() -> bool:
        """ECS環境で実行されているかを判定"""
        return os.environ.get("ECS_CONTAINER_METADATA_URI_V4") is not None

    @staticmethod
    def setup_page_config() -> None:
        """Streamlitページ設定"""
        st.set_page_config(**STREAMLIT_CONFIG)

    @staticmethod
    def render_header() -> None:
        """ヘッダー部分をレンダリング"""
        st.title("☁️ AWS Resource Visualizer")
        st.markdown("AWSアカウント内の主要リソースを可視化します")

    def render_sidebar_settings(
        self,
    ) -> Tuple[Optional[str], str, List[str], bool, bool]:
        """サイドバーの設定部分をレンダリング

        Returns:
            Tuple[Optional[str], str, List[str], bool, bool]: (
                selected_profile, selected_region, selected_services,
                refresh_button, clear_cache
            )
        """
        st.sidebar.header("🔄 データ更新")

        refresh_button, clear_cache = self._render_data_update_controls()

        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ 設定")

        selected_profile = self._render_profile_selection()
        self._handle_profile_change(selected_profile)

        selected_region = self._render_region_selection()
        self._handle_region_change(selected_region)

        selected_services = self._render_service_selection()

        return (
            selected_profile,
            selected_region,
            selected_services,
            refresh_button,
            clear_cache,
        )

    def _render_profile_selection(self) -> Optional[str]:
        """プロファイル選択UIをレンダリング"""
        if self.running_on_ecs:
            st.sidebar.info("🚀 ECS環境で実行中")
            st.sidebar.text("認証: タスクロール使用")
            return None
        else:
            default_profile_index = 0
            if DEFAULT_PROFILE in AVAILABLE_PROFILES:
                default_profile_index = AVAILABLE_PROFILES.index(
                    DEFAULT_PROFILE
                )

            selected_profile = st.sidebar.selectbox(
                "AWSプロファイルを選択",
                options=AVAILABLE_PROFILES,
                index=default_profile_index,
                help="使用するAWSプロファイルを選択してください",
            )
            return (
                str(selected_profile) if selected_profile is not None else None
            )

    def _handle_profile_change(self, selected_profile: Optional[str]) -> None:
        """プロファイル変更時の処理"""
        if self.running_on_ecs:
            return

        if "previous_profile" not in st.session_state:
            st.session_state.previous_profile = selected_profile
        elif st.session_state.previous_profile != selected_profile:
            # ページネーションをリセット
            for service in SUPPORTED_SERVICES.keys():
                for region in SUPPORTED_REGIONS:
                    reset_pagination(key_prefix=f"{service}_{region}")

            st.session_state.previous_profile = selected_profile

            # 新しい状態管理システムでリセット
            # Local Library
            from ..shared.state_manager import get_state_manager

            state_manager = get_state_manager()
            state_manager.reset_app_state()

            # キャッシュ情報を強制更新
            st.session_state.cache_info_updated = True

    def _render_region_selection(self) -> str:
        """リージョン選択UIをレンダリング"""
        if self.running_on_ecs:
            selected_region = os.environ.get(
                "AWS_DEFAULT_REGION", DEFAULT_REGION
            )
            st.sidebar.text(f"リージョン: {selected_region}")
            return selected_region
        else:
            default_region_index = 0
            if DEFAULT_REGION in SUPPORTED_REGIONS:
                default_region_index = SUPPORTED_REGIONS.index(DEFAULT_REGION)

            selected_region = st.sidebar.selectbox(
                "リージョンを選択",
                options=SUPPORTED_REGIONS,
                index=default_region_index,
            )
            return str(selected_region)

    def _handle_region_change(self, selected_region: str) -> None:
        """リージョン変更時の処理"""
        if self.running_on_ecs:
            return

        if "previous_region" not in st.session_state:
            st.session_state.previous_region = selected_region
        elif st.session_state.previous_region != selected_region:
            for service in SUPPORTED_SERVICES.keys():
                reset_pagination(key_prefix=f"{service}_{selected_region}")
                reset_pagination(
                    key_prefix=f"{service}_{st.session_state.previous_region}"
                )
            st.session_state.previous_region = selected_region

            # キャッシュ情報を強制更新
            st.session_state.cache_info_updated = True

    def _render_service_selection(self) -> List[str]:
        """サービス選択UIをレンダリング"""
        selected: List[str] = st.sidebar.multiselect(
            "表示するサービスを選択",
            options=list(SUPPORTED_SERVICES.keys()),
            default=DEFAULT_SERVICES,
        )
        return selected

    def _render_data_update_controls(self) -> Tuple[bool, bool]:
        """データ更新コントロールをサイドバーでレンダリング"""
        # Local Library
        from ..shared.state_manager import get_state_manager

        state_manager = get_state_manager()
        running_tasks = state_manager.get_running_executions()
        has_running_tasks = len(running_tasks) > 0

        # 実行中タスクの表示
        if has_running_tasks:
            st.sidebar.warning("⚠️ 実行中のタスク")
            for task in running_tasks:
                duration = task.get("lock_info", {}).get("duration", 0)
                if duration:
                    st.sidebar.text(
                        f"• {task['region']}: {int(duration)}秒経過"
                    )
                else:
                    st.sidebar.text(f"• {task['region']}: 実行中")

            # 実行中タスクがある場合は、経過時間を更新するため自動更新
            # Standard Library
            import time

            time.sleep(1)
            st.rerun()

        refresh_button = st.sidebar.button(
            "🔄 データを更新",
            type="primary",
            use_container_width=True,
            disabled=has_running_tasks,
            help=(
                "実行中は無効化されます"
                if has_running_tasks
                else "選択したサービスのリソース情報を取得します"
            ),
        )

        clear_cache = st.sidebar.checkbox(
            "キャッシュをクリアして最新データを取得",
            value=False,
            disabled=has_running_tasks,
            help=(
                "実行中は変更できません"
                if has_running_tasks
                else "チェックすると、キャッシュされたデータを無視して最新のデータを取得します"
            ),
        )

        return refresh_button, clear_cache

    def render_cache_info(
        self,
        selected_profile: Optional[str],
        selected_region: str,
        selected_services: List[str],
    ) -> None:
        """キャッシュ情報をサイドバーに表示"""
        st.sidebar.markdown("---")
        st.sidebar.subheader("🗄️ キャッシュ情報")

        if st.sidebar.button(
            "🗑️ キャッシュをクリア",
            help="すべてのキャッシュデータを削除します",
            use_container_width=True,
        ):
            self._handle_cache_clear()

        # Local Library
        from ..shared.cache_manager import get_cache_instance

        cache = get_cache_instance()
        data_just_fetched = st.session_state.get("data_just_fetched", False)
        cache_info_updated = st.session_state.get("cache_info_updated", False)

        # data_just_fetchedフラグを先にクリア
        if data_just_fetched:
            st.session_state.data_just_fetched = False

        # cache_info_updatedフラグをクリア
        if cache_info_updated:
            st.session_state.cache_info_updated = False

        # 現在の選択に対するキャッシュ状況を確認（新しいメソッドを使用）
        cache_summary = cache.get_cache_summary_for_combination(
            selected_services, selected_region, selected_profile
        )
        has_valid_cache = cache_summary["has_any_cache"]

        cache_size = cache.get_cache_size()

        if has_valid_cache or data_just_fetched:
            if (
                cache_summary["valid_caches"]
                == cache_summary["total_services"]
            ):
                st.sidebar.success("✅ キャッシュ有効（全サービス）")
            else:
                st.sidebar.warning(
                    f"⚠️ キャッシュ部分有効（{cache_summary['valid_caches']}/{cache_summary['total_services']}サービス）"
                )

            # データ取得時刻を表示
            if data_just_fetched:
                current_time = datetime.now()
                with st.sidebar.expander("🕒 データ取得時刻", expanded=False):
                    st.text(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                # キャッシュ有効期限を表示
                expire_time = current_time + timedelta(seconds=CACHE_TTL)
                with st.sidebar.expander(
                    "📅 キャッシュ有効期限", expanded=False
                ):
                    st.text(expire_time.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                if cache_summary["latest_fetch_time"]:
                    with st.sidebar.expander(
                        "🕒 データ取得時刻", expanded=False
                    ):
                        st.text(cache_summary["latest_fetch_time"])

                if cache_summary["earliest_expire_time"]:
                    with st.sidebar.expander(
                        "📅 キャッシュ有効期限", expanded=False
                    ):
                        st.text(cache_summary["earliest_expire_time"])
        else:
            st.sidebar.info("ℹ️ キャッシュなし")
            if cache_size["file_count"] > 0:
                st.sidebar.caption(
                    f"他の設定のキャッシュ: {cache_size['file_count']}ファイル"
                )

        with st.sidebar.expander("🔧 現在の設定", expanded=True):
            if self.running_on_ecs:
                st.markdown(
                    "🔑 **認証方式**:<br>タスクロール", unsafe_allow_html=True
                )
                st.markdown(
                    f"🌍 **使用中リージョン**:<br>{selected_region}",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"🔑 **使用中プロファイル**:<br>{selected_profile}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"🌍 **使用中リージョン**:<br>{selected_region}",
                    unsafe_allow_html=True,
                )

    def _handle_cache_clear(self) -> None:
        """キャッシュクリア処理"""
        # Local Library
        from ..shared.cache_manager import get_cache_instance
        from ..shared.state_manager import get_state_manager

        cache = get_cache_instance()
        cleared_count = cache.clear_cache()

        # AppStateをリセット
        state_manager = get_state_manager()
        state_manager.reset_app_state()

        # すべてのステータスファイルをクリア
        status_cleared = state_manager.clear_all_status_files()

        st.sidebar.success(
            f"キャッシュをクリアしました（{cleared_count}ファイル + {status_cleared}ステータス削除）"
        )
        st.rerun()

    def render_no_services_warning(self) -> None:
        """サービス未選択時の警告表示"""
        st.warning("⚠️ 表示するサービスを選択してください")
        st.info("👈 サイドバーから1つ以上のサービスを選択してください")

    def render_authentication_error(self, profile: Optional[str]) -> None:
        """認証エラー表示"""
        if profile:
            st.error(
                f"❌ AWS認証エラー: プロファイル '{profile}' の認証情報を確認してください"
            )
        else:
            st.error("❌ AWS認証エラー: 認証情報を確認してください")

        with st.expander("🔧 認証設定の確認方法"):
            if profile:
                st.code(f"aws configure --profile {profile}")
                st.code(f"aws sts get-caller-identity --profile {profile}")
            else:
                st.code("aws configure")
                st.code("aws sts get-caller-identity")

    def render_batch_started_success(self) -> None:
        """バッチ開始成功メッセージ"""
        pass  # メッセージ表示を削除

    def render_status_ui(
        self,
        selected_services: List[str],
        selected_region: str,
        selected_profile: Optional[str],
    ) -> None:
        """ステータスに応じたUI表示"""
        # Local Library
        from ..shared.state_manager import get_state_manager

        state_manager = get_state_manager()

        if state_manager.is_loading():
            # シンプルなローディング表示
            st.info("🔄 データ取得中...")
            # 設定された間隔で継続的に自動更新
            # Standard Library
            import time

            # Local Library
            from ..shared.config import AUTO_REFRESH_INTERVAL

            time.sleep(AUTO_REFRESH_INTERVAL)
            st.rerun()

        elif state_manager.is_error():
            st.error(f"❌ エラーが発生しました: {state_manager.error_message}")

    def render_initial_info_display(
        self, selected_services: List[str]
    ) -> None:
        """初期情報表示（データが読み込まれていない場合）"""
        st.info(
            "👈 「データを更新」ボタンを押してリソース情報を取得してください"
        )

        st.markdown("---")
        st.markdown("### 📋 取得可能な情報")

        # サービス別の取得情報を表示
        for service in selected_services:
            with st.expander(f"{service} で取得される情報"):
                if service == "EC2":
                    st.markdown(
                        """
                    - Instance ID
                    - インスタンス名（Name タグ）
                    - 状態（running, stopped など）
                    - インスタンスタイプ
                    - アベイラビリティゾーン
                    - パブリック IP アドレス
                    - タグ情報
                    """
                    )
                elif service == "RDS":
                    st.markdown(
                        """
                    - DB インスタンス識別子
                    - データベースエンジン
                    - DB インスタンスクラス
                    - ステータス
                    - 作成日時
                    - タグ情報
                    """
                    )
                elif service == "S3":
                    st.markdown(
                        """
                    - バケット名
                    - 作成日時
                    - パブリック設定（ACL）
                    - タグ情報
                    """
                    )
                elif service == "Lambda":
                    st.markdown(
                        """
                    - 関数名
                    - ランタイム
                    - メモリサイズ
                    - 最終更新日時
                    - タグ情報
                    """
                    )


# シングルトンインスタンス
_sidebar_ui_instance = None


def get_sidebar_ui() -> SidebarUI:
    """SidebarUIのシングルトンインスタンスを取得"""
    global _sidebar_ui_instance
    if _sidebar_ui_instance is None:
        _sidebar_ui_instance = SidebarUI()
    return _sidebar_ui_instance
