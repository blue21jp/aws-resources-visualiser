#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - メインアプリケーション"""

# Standard Library
from typing import Optional

# Third Party Library
import boto3
import streamlit as st

# Local Library
from ..shared.state_manager import get_state_manager
from .batch_processor import get_batch_processor
from .main_content_ui import get_main_content_ui
from .pagination import reset_pagination
from .sidebar_ui import get_sidebar_ui
from .tag_filter import render_tag_filter_ui


def validate_aws_authentication(selected_profile: Optional[str]) -> bool:
    """AWS認証情報の確認"""
    try:
        session = boto3.Session(
            profile_name=(
                selected_profile if selected_profile != "default" else None
            )
        )
        credentials = session.get_credentials()
        if credentials is None:
            return False
        # 実際に認証情報にアクセスして有効性を確認
        _ = credentials.access_key
        return True
    except Exception:
        return False


def main() -> None:
    """Streamlitアプリのメイン関数"""
    # 統合クラスのインスタンスを取得
    sidebar_ui = get_sidebar_ui()
    main_content_ui = get_main_content_ui()
    state_manager = get_state_manager()
    batch_processor = get_batch_processor()

    # 初期化
    sidebar_ui.setup_page_config()
    sidebar_ui.render_header()

    # サイドバー設定
    (
        selected_profile,
        selected_region,
        selected_services,
        refresh_button,
        clear_cache,
    ) = sidebar_ui.render_sidebar_settings()

    # サービス未選択チェック
    if not selected_services:
        sidebar_ui.render_no_services_warning()
        return

    # 実行環境に応じたタイトル表示
    # Local Library
    from ..shared.config import BATCH_RUN_TYPE

    if BATCH_RUN_TYPE == "ecs":
        # ECS環境ではプロファイル情報を表示しない
        st.title(f"{selected_region}のリソース情報")
    else:
        # ローカル・Docker環境ではプロファイル情報を表示
        profile_display = selected_profile if selected_profile else "default"
        st.title(f"{profile_display}({selected_region})のリソース情報")

    # 設定変更検知とデータリセット
    _handle_settings_change(
        selected_profile,
        selected_region,
        selected_services,
        state_manager,
        batch_processor,
    )

    # 初期状態チェック
    _check_initial_status(
        selected_services,
        selected_region,
        selected_profile,
        batch_processor,
        state_manager,
    )

    # データ更新処理
    if refresh_button:
        _handle_refresh(
            selected_profile,
            selected_services,
            selected_region,
            clear_cache,
            sidebar_ui,
            batch_processor,
        )

    # ステータスに応じたUI表示
    sidebar_ui.render_status_ui(
        selected_services, selected_region, selected_profile
    )

    # タグフィルター表示
    tag_filters = {}
    if state_manager.is_completed() and state_manager.has_data():
        tag_filters = render_tag_filter_ui(state_manager.data)

    # キャッシュ情報表示
    sidebar_ui.render_cache_info(
        selected_profile, selected_region, selected_services
    )

    # メインコンテンツ表示
    _render_main_content(
        selected_services,
        selected_region,
        tag_filters,
        main_content_ui,
        state_manager,
        sidebar_ui,
    )


def _handle_settings_change(
    profile: Optional[str],
    region: str,
    services: list,
    state_manager,
    batch_processor,
) -> None:
    """設定変更を検知してデータをリセット・再読み込み"""
    # 現在の設定をキーとして生成
    current_settings_key = f"{profile}_{region}_{sorted(services)}"

    # 前回の設定と比較
    if "last_settings_key" not in st.session_state:
        st.session_state.last_settings_key = current_settings_key
        return

    # 設定が変更された場合
    if st.session_state.last_settings_key != current_settings_key:
        # アプリケーション状態をリセット
        state_manager.reset_app_state()

        # ページネーションをリセット
        for service in services:
            reset_pagination(key_prefix=f"{service}_{region}")

        # キャッシュ情報を強制更新
        st.session_state.cache_info_updated = True

        # 設定を更新
        st.session_state.last_settings_key = current_settings_key


def _check_initial_status(
    services: list,
    region: str,
    profile: Optional[str],
    batch_processor,
    state_manager,
) -> None:
    """初期状態のチェック"""
    # データが既にある場合はスキップ
    if state_manager.has_data():
        return

    execution_info = batch_processor.get_execution_status(
        services, region, profile
    )
    status = execution_info.get("status")

    if status == "running":
        state_manager.set_loading()
    elif status == "completed":
        # キャッシュからデータを読み込み
        batch_processor._load_data_from_cache(services, region, profile)
        if state_manager.has_data():
            state_manager.set_completed(state_manager.data)
    elif status == "failed":
        error_msg = execution_info.get("error", "不明なエラー")
        state_manager.set_error(f"前回のバッチ実行でエラーが発生: {error_msg}")


def _handle_refresh(
    profile: Optional[str],
    services: list,
    region: str,
    clear_cache: bool,
    sidebar_ui,
    batch_processor,
) -> None:
    """データ更新処理"""
    # AWS認証チェック
    if not validate_aws_authentication(profile):
        sidebar_ui.render_authentication_error(profile)
        return

    # ページネーションリセット
    for service in services:
        reset_pagination(key_prefix=f"{service}_{region}")

    # バッチ実行（WebUIからは常にforce=False）
    result = batch_processor.handle_execution(
        services, region, profile, clear_cache, force=False
    )

    if result == "started":
        sidebar_ui.render_batch_started_success()


def _render_main_content(
    services: list,
    region: str,
    tag_filters: dict,
    main_content_ui,
    state_manager,
    sidebar_ui,
) -> None:
    """メインコンテンツの表示"""
    if state_manager.is_loading():
        # ローディング中は何も表示しない（自動更新のみ）
        return

    if not state_manager.is_completed() or not state_manager.has_data():
        sidebar_ui.render_initial_info_display(services)
        return

    main_content_ui.render_data_tabs(
        services, region, tag_filters, state_manager.data
    )


if __name__ == "__main__":
    main()
