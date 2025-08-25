#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - ページネーション"""

# Standard Library
from typing import Any, Dict, Tuple

# Third Party Library
import pandas as pd
import streamlit as st


def paginate_dataframe(
    data: pd.DataFrame, page_size: int = 10, key_prefix: str = "pagination"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    DataFrameをページネーション表示する

    Args:
        data: 表示するDataFrame
        page_size: 1ページあたりの表示件数
        key_prefix: セッション状態のキーのプレフィックス

    Returns:
        Tuple[pd.DataFrame, Dict]: (表示用DataFrame, ページネーション情報)
    """
    if data.empty:
        return data, {
            "total_items": 0,
            "total_pages": 0,
            "current_page": 1,
            "start_index": 0,
            "end_index": 0,
        }

    total_items = len(data)
    total_pages = (total_items - 1) // page_size + 1

    # セッション状態のキー
    page_key = f"{key_prefix}_current_page"

    # 現在のページを取得（デフォルトは1）
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current_page = st.session_state[page_key]

    # ページ番号の範囲チェック
    if current_page < 1:
        current_page = 1
        st.session_state[page_key] = current_page
    elif current_page > total_pages:
        current_page = total_pages
        st.session_state[page_key] = current_page

    # 表示範囲を計算
    start_index = (current_page - 1) * page_size
    end_index = min(start_index + page_size, total_items)

    # 表示用データを切り出し
    paginated_data = data.iloc[start_index:end_index]

    pagination_info = {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": current_page,
        "start_index": start_index,
        "end_index": end_index,
        "page_size": page_size,
    }

    return paginated_data, pagination_info


def render_pagination_controls(
    pagination_info: Dict[str, Any],
    key_prefix: str = "pagination",
    control_id: str = "default",
) -> None:
    """
    ページネーションコントロールを表示する

    Args:
        pagination_info: ページネーション情報
        key_prefix: セッション状態のキーのプレフィックス
        control_id: コントロールの識別子（上部/下部で異なるキーを使用するため）
    """
    if pagination_info["total_pages"] <= 1:
        return

    page_key = f"{key_prefix}_current_page"
    current_page = pagination_info["current_page"]
    total_pages = pagination_info["total_pages"]

    # コントロール用のユニークキー
    unique_key = f"{key_prefix}_{control_id}"

    # ページネーションコントロールを表示
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        # 最初のページボタン
        if st.button(
            "⏮️ 最初", disabled=(current_page == 1), key=f"{unique_key}_first"
        ):
            st.session_state[page_key] = 1
            st.rerun()

    with col2:
        # 前のページボタン
        if st.button(
            "◀️ 前", disabled=(current_page == 1), key=f"{unique_key}_prev"
        ):
            st.session_state[page_key] = current_page - 1
            st.rerun()

    with col3:
        # ページ情報表示とページ選択
        page_options = list(range(1, total_pages + 1))
        selected_page = st.selectbox(
            f"ページ {current_page} / {total_pages}",
            options=page_options,
            index=current_page - 1,
            key=f"{unique_key}_select",
            label_visibility="collapsed",
        )

        if selected_page != current_page:
            st.session_state[page_key] = selected_page
            st.rerun()

    with col4:
        # 次のページボタン
        if st.button(
            "▶️ 次",
            disabled=(current_page == total_pages),
            key=f"{unique_key}_next",
        ):
            st.session_state[page_key] = current_page + 1
            st.rerun()

    with col5:
        # 最後のページボタン
        if st.button(
            "⏭️ 最後",
            disabled=(current_page == total_pages),
            key=f"{unique_key}_last",
        ):
            st.session_state[page_key] = total_pages
            st.rerun()


def render_pagination_info(pagination_info: Dict[str, Any]) -> None:
    """
    ページネーション情報を表示する

    Args:
        pagination_info: ページネーション情報
    """
    if pagination_info["total_items"] == 0:
        st.info("表示するデータがありません")
        return

    start_num = pagination_info["start_index"] + 1
    end_num = pagination_info["end_index"]
    total_num = pagination_info["total_items"]

    st.caption(f"📊 {start_num}-{end_num} / {total_num} 件を表示")


def reset_pagination(key_prefix: str = "pagination") -> None:
    """
    ページネーション状態をリセットする

    Args:
        key_prefix: セッション状態のキーのプレフィックス
    """
    page_key = f"{key_prefix}_current_page"
    if page_key in st.session_state:
        st.session_state[page_key] = 1
