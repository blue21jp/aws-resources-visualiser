#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - タグフィルター"""

# Standard Library
from typing import Dict, Set

# Third Party Library
import pandas as pd
import streamlit as st

# Local Library
from ..shared.config import REQUIRED_TAGS


def get_required_tag_values_for_key(
    all_data: Dict[str, pd.DataFrame], tag_key: str
) -> Set[str]:
    """指定された必須タグキーの全ての値を取得"""
    tag_values = set()

    for service, data in all_data.items():
        if not data.empty and "Tags Dict" in data.columns:
            for _, row in data.iterrows():
                tags_dict = row.get("Tags Dict", {})
                if isinstance(tags_dict, dict) and tag_key in tags_dict:
                    tag_values.add(tags_dict[tag_key])

    return tag_values


def filter_data_by_tags(
    data: pd.DataFrame, tag_filters: Dict[str, str]
) -> pd.DataFrame:
    """タグフィルタに基づいてデータをフィルタリング"""
    if data.empty or "Tags Dict" not in data.columns or not tag_filters:
        return data

    filtered_indices = []

    for idx, row in data.iterrows():
        tags_dict = row.get("Tags Dict", {})
        if not isinstance(tags_dict, dict):
            continue

        # 全てのフィルタ条件を満たすかチェック
        matches_all_filters = True
        for filter_key, filter_value in tag_filters.items():
            if (
                filter_key not in tags_dict
                or tags_dict[filter_key] != filter_value
            ):
                matches_all_filters = False
                break

        if matches_all_filters:
            filtered_indices.append(idx)

    return data.loc[filtered_indices] if filtered_indices else pd.DataFrame()


def render_tag_filter_ui(all_data: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """必須タグのみのフィルタUIを描画し、選択されたフィルタを返す"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏷️ 必須タグフィルタ")

    # フィルタが有効かどうかのチェックボックス
    enable_filter = st.sidebar.checkbox(
        "必須タグフィルタを有効にする",
        value=False,
        help="チェックすると必須タグの値でリソースをフィルタできます",
    )

    tag_filters: Dict[str, str] = {}

    if enable_filter:
        # 必須タグのみを選択肢として提供
        if not REQUIRED_TAGS:
            st.sidebar.info("必須タグが設定されていません")
            return tag_filters

        # 必須タグキーを選択
        selected_tag_key = st.sidebar.selectbox(
            "必須タグキーを選択",
            options=[""] + list(REQUIRED_TAGS),
            help="フィルタに使用する必須タグキーを選択してください",
        )

        if selected_tag_key:
            # 選択された必須タグキーの値を取得
            available_tag_values = get_required_tag_values_for_key(
                all_data, selected_tag_key
            )

            if available_tag_values:
                selected_tag_value = st.sidebar.selectbox(
                    f"'{selected_tag_key}' の値を選択",
                    options=[""] + sorted(list(available_tag_values)),
                    help=f"'{selected_tag_key}' タグの値を選択してください",
                )

                if selected_tag_value:
                    tag_filters[selected_tag_key] = selected_tag_value

                    # フィルタ条件を表示
                    st.sidebar.success(
                        f"✅ フィルタ: {selected_tag_key}={selected_tag_value}"
                    )
            else:
                st.sidebar.warning(
                    f"'{selected_tag_key}' に対応する値が見つかりません"
                )

    return tag_filters


def get_filtered_resource_count(
    all_data: Dict[str, pd.DataFrame], tag_filters: Dict[str, str]
) -> Dict[str, int]:
    """フィルタ適用後のリソース数を取得"""
    filtered_counts = {}

    for service, data in all_data.items():
        if not data.empty:
            filtered_data = filter_data_by_tags(data, tag_filters)
            filtered_counts[service] = len(filtered_data)
        else:
            filtered_counts[service] = 0

    return filtered_counts
