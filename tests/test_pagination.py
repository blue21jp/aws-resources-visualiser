#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - ページネーション機能のテスト"""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party Library
import pandas as pd

# First Party Library
from app.web.pagination import (
    paginate_dataframe,
    render_pagination_controls,
    render_pagination_info,
    reset_pagination,
)


class TestPaginateDataframe:
    """paginate_dataframe関数のテスト"""

    def test_empty_dataframe(self):
        """空のDataFrameのテスト"""
        empty_df = pd.DataFrame()
        result_df, pagination_info = paginate_dataframe(empty_df)

        assert result_df.empty
        assert pagination_info == {
            "total_items": 0,
            "total_pages": 0,
            "current_page": 1,
            "start_index": 0,
            "end_index": 0,
        }

    def test_single_page_data(self):
        """1ページに収まるデータのテスト"""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        with patch("streamlit.session_state", {}):
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert len(result_df) == 3
        assert pagination_info["total_items"] == 3
        assert pagination_info["total_pages"] == 1
        assert pagination_info["current_page"] == 1
        assert pagination_info["start_index"] == 0
        assert pagination_info["end_index"] == 3

    def test_multiple_pages_data(self):
        """複数ページにわたるデータのテスト"""
        df = pd.DataFrame(
            {"col1": list(range(25)), "col2": [f"item_{i}" for i in range(25)]}
        )

        with patch("streamlit.session_state", {}):
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert len(result_df) == 10
        assert pagination_info["total_items"] == 25
        assert pagination_info["total_pages"] == 3
        assert pagination_info["current_page"] == 1
        assert pagination_info["start_index"] == 0
        assert pagination_info["end_index"] == 10

    def test_custom_page_size(self):
        """カスタムページサイズのテスト"""
        df = pd.DataFrame({"col1": list(range(15))})

        with patch("streamlit.session_state", {}):
            result_df, pagination_info = paginate_dataframe(df, page_size=5)

        assert len(result_df) == 5
        assert pagination_info["total_pages"] == 3
        assert pagination_info["page_size"] == 5

    def test_custom_key_prefix(self):
        """カスタムキープレフィックスのテスト"""
        df = pd.DataFrame({"col1": [1, 2, 3]})

        with patch("streamlit.session_state", {}) as mock_session:
            paginate_dataframe(df, key_prefix="custom")
            assert "custom_current_page" in mock_session

    def test_existing_page_state(self):
        """既存のページ状態があるテスト"""
        df = pd.DataFrame({"col1": list(range(25))})

        with patch("streamlit.session_state", {"pagination_current_page": 2}):
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert pagination_info["current_page"] == 2
        assert pagination_info["start_index"] == 10
        assert pagination_info["end_index"] == 20

    def test_page_out_of_range_high(self):
        """ページ番号が範囲外（大きすぎる）のテスト"""
        df = pd.DataFrame({"col1": list(range(15))})

        with patch(
            "streamlit.session_state", {"pagination_current_page": 10}
        ) as mock_session:
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert pagination_info["current_page"] == 2  # 最大ページに修正される
        assert mock_session["pagination_current_page"] == 2

    def test_page_out_of_range_low(self):
        """ページ番号が範囲外（小さすぎる）のテスト"""
        df = pd.DataFrame({"col1": list(range(15))})

        with patch(
            "streamlit.session_state", {"pagination_current_page": 0}
        ) as mock_session:
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert pagination_info["current_page"] == 1  # 最小ページに修正される
        assert mock_session["pagination_current_page"] == 1

    def test_last_page_partial_data(self):
        """最後のページが部分的なデータのテスト"""
        df = pd.DataFrame({"col1": list(range(23))})

        with patch("streamlit.session_state", {"pagination_current_page": 3}):
            result_df, pagination_info = paginate_dataframe(df, page_size=10)

        assert len(result_df) == 3  # 最後のページは3件のみ
        assert pagination_info["start_index"] == 20
        assert pagination_info["end_index"] == 23


class TestRenderPaginationControls:
    """render_pagination_controls関数のテスト"""

    @patch("streamlit.columns")
    @patch("streamlit.button")
    @patch("streamlit.selectbox")
    @patch("streamlit.rerun")
    def test_render_controls_multiple_pages(
        self, mock_rerun, mock_selectbox, mock_button, mock_columns
    ):
        """複数ページの場合のコントロール表示テスト"""
        mock_columns.return_value = [MagicMock() for _ in range(5)]
        mock_button.return_value = False
        mock_selectbox.return_value = 1

        pagination_info = {
            "total_pages": 3,
            "current_page": 2,
        }

        with patch("streamlit.session_state", {}):
            render_pagination_controls(pagination_info)

        # columnsが呼ばれることを確認
        mock_columns.assert_called_once()

    @patch("streamlit.columns")
    def test_render_controls_single_page(self, mock_columns):
        """単一ページの場合のコントロール表示テスト（何も表示されない）"""
        pagination_info = {
            "total_pages": 1,
            "current_page": 1,
        }

        render_pagination_controls(pagination_info)

        # 単一ページの場合は何も表示されない
        mock_columns.assert_not_called()

    @patch("streamlit.columns")
    @patch("streamlit.button")
    @patch("streamlit.selectbox")
    @patch("streamlit.rerun")
    def test_button_interactions(
        self, mock_rerun, mock_selectbox, mock_button, mock_columns
    ):
        """ボタンクリック時の動作テスト"""
        mock_columns.return_value = [MagicMock() for _ in range(5)]
        mock_selectbox.return_value = 2

        pagination_info = {
            "total_pages": 5,
            "current_page": 3,
        }

        # 最初のボタンがクリックされた場合
        mock_button.side_effect = [True, False, False, False]

        with patch("streamlit.session_state", {"pagination_current_page": 3}):
            render_pagination_controls(pagination_info)

        # rerunが呼ばれることを確認（複数回呼ばれる可能性がある）
        assert mock_rerun.call_count >= 1

    @patch("streamlit.columns")
    @patch("streamlit.button")
    @patch("streamlit.selectbox")
    @patch("streamlit.rerun")
    def test_selectbox_change(
        self, mock_rerun, mock_selectbox, mock_button, mock_columns
    ):
        """セレクトボックス変更時の動作テスト"""
        mock_columns.return_value = [MagicMock() for _ in range(5)]
        mock_button.return_value = False
        mock_selectbox.return_value = 4  # 異なるページを選択

        pagination_info = {
            "total_pages": 5,
            "current_page": 2,
        }

        with patch("streamlit.session_state", {"pagination_current_page": 2}):
            render_pagination_controls(pagination_info)

        # rerunが呼ばれることを確認（複数回呼ばれる可能性がある）
        assert mock_rerun.call_count >= 1


class TestRenderPaginationInfo:
    """render_pagination_info関数のテスト"""

    @patch("streamlit.info")
    def test_render_info_no_data(self, mock_info):
        """データがない場合の情報表示テスト"""
        pagination_info = {"total_items": 0}

        render_pagination_info(pagination_info)

        mock_info.assert_called_once_with("表示するデータがありません")

    @patch("streamlit.caption")
    def test_render_info_with_data(self, mock_caption):
        """データがある場合の情報表示テスト"""
        pagination_info = {
            "total_items": 25,
            "start_index": 10,
            "end_index": 20,
        }

        render_pagination_info(pagination_info)

        mock_caption.assert_called_once_with("📊 11-20 / 25 件を表示")

    @patch("streamlit.caption")
    def test_render_info_first_page(self, mock_caption):
        """最初のページの情報表示テスト"""
        pagination_info = {
            "total_items": 15,
            "start_index": 0,
            "end_index": 10,
        }

        render_pagination_info(pagination_info)

        mock_caption.assert_called_once_with("📊 1-10 / 15 件を表示")


class TestResetPagination:
    """reset_pagination関数のテスト"""

    def test_reset_existing_pagination(self):
        """既存のページネーション状態をリセットするテスト"""
        with patch(
            "streamlit.session_state", {"pagination_current_page": 5}
        ) as mock_session:
            reset_pagination()

        assert mock_session["pagination_current_page"] == 1

    def test_reset_non_existing_pagination(self):
        """存在しないページネーション状態をリセットするテスト"""
        with patch("streamlit.session_state", {}) as mock_session:
            reset_pagination()

        # キーが存在しない場合は何もしない
        assert "pagination_current_page" not in mock_session

    def test_reset_custom_key_prefix(self):
        """カスタムキープレフィックスでのリセットテスト"""
        with patch(
            "streamlit.session_state", {"custom_current_page": 3}
        ) as mock_session:
            reset_pagination("custom")

        assert mock_session["custom_current_page"] == 1

    def test_reset_multiple_keys(self):
        """複数のキーがある場合のリセットテスト"""
        with patch(
            "streamlit.session_state",
            {
                "pagination_current_page": 5,
                "other_pagination_current_page": 3,
                "unrelated_key": "value",
            },
        ) as mock_session:
            reset_pagination()

        assert mock_session["pagination_current_page"] == 1
        assert (
            mock_session["other_pagination_current_page"] == 3
        )  # 他のキーは変更されない
        assert (
            mock_session["unrelated_key"] == "value"
        )  # 関係ないキーは変更されない
