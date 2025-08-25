#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - タグフィルター機能のテスト"""

# Standard Library
from typing import Any, Dict
from unittest.mock import patch

# Third Party Library
import pandas as pd

# First Party Library
from app.web.tag_filter import (
    filter_data_by_tags,
    get_filtered_resource_count,
    get_required_tag_values_for_key,
    render_tag_filter_ui,
)


class TestGetRequiredTagValuesForKey:
    """get_required_tag_values_for_key関数のテスト"""

    def test_empty_data(self):
        """空のデータのテスト"""
        all_data: Dict[str, Any] = {}
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == set()

    def test_no_tags_dict_column(self):
        """Tags Dict列がないデータのテスト"""
        all_data = {"EC2": pd.DataFrame({"Name": ["instance1", "instance2"]})}
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == set()

    def test_empty_dataframe(self):
        """空のDataFrameのテスト"""
        all_data = {"EC2": pd.DataFrame()}
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == set()

    def test_valid_tag_values(self):
        """有効なタグ値があるデータのテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2"],
                    "Tags Dict": [
                        {"CostProject": "project-a", "Environment": "dev"},
                        {"CostProject": "project-b", "Environment": "prod"},
                    ],
                }
            ),
            "RDS": pd.DataFrame(
                {
                    "Name": ["db1"],
                    "Tags Dict": [
                        {"CostProject": "project-a", "Environment": "dev"}
                    ],
                }
            ),
        }
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == {"project-a", "project-b"}

    def test_missing_tag_key(self):
        """指定されたタグキーがないデータのテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"Environment": "dev", "Owner": "team1"}],
                }
            )
        }
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == set()

    def test_invalid_tags_dict(self):
        """無効なTags Dictのテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2"],
                    "Tags Dict": [
                        {"CostProject": "project-a"},
                        "invalid_dict",  # 辞書ではない
                    ],
                }
            )
        }
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == {"project-a"}

    def test_multiple_services(self):
        """複数サービスからのタグ値取得テスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "web-app"}],
                }
            ),
            "RDS": pd.DataFrame(
                {"Name": ["db1"], "Tags Dict": [{"CostProject": "database"}]}
            ),
            "S3": pd.DataFrame(
                {
                    "Name": ["bucket1"],
                    "Tags Dict": [{"CostProject": "web-app"}],  # 重複値
                }
            ),
        }
        result = get_required_tag_values_for_key(all_data, "CostProject")
        assert result == {"web-app", "database"}


class TestFilterDataByTags:
    """filter_data_by_tags関数のテスト"""

    def test_empty_dataframe(self):
        """空のDataFrameのテスト"""
        data = pd.DataFrame()
        tag_filters = {"CostProject": "project-a"}
        result = filter_data_by_tags(data, tag_filters)
        assert result.empty

    def test_no_tags_dict_column(self):
        """Tags Dict列がないデータのテスト"""
        data = pd.DataFrame({"Name": ["instance1", "instance2"]})
        tag_filters = {"CostProject": "project-a"}
        result = filter_data_by_tags(data, tag_filters)
        pd.testing.assert_frame_equal(result, data)

    def test_empty_tag_filters(self):
        """空のタグフィルタのテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1"],
                "Tags Dict": [{"CostProject": "project-a"}],
            }
        )
        tag_filters: Dict[str, Any] = {}
        result = filter_data_by_tags(data, tag_filters)
        pd.testing.assert_frame_equal(result, data)

    def test_single_filter_match(self):
        """単一フィルタでマッチするテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1", "instance2", "instance3"],
                "Tags Dict": [
                    {"CostProject": "project-a", "Environment": "dev"},
                    {"CostProject": "project-b", "Environment": "prod"},
                    {"CostProject": "project-a", "Environment": "test"},
                ],
            }
        )
        tag_filters = {"CostProject": "project-a"}
        result = filter_data_by_tags(data, tag_filters)

        assert len(result) == 2
        assert result["Name"].tolist() == ["instance1", "instance3"]

    def test_multiple_filters_match(self):
        """複数フィルタでマッチするテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1", "instance2", "instance3"],
                "Tags Dict": [
                    {"CostProject": "project-a", "Environment": "dev"},
                    {"CostProject": "project-a", "Environment": "prod"},
                    {"CostProject": "project-b", "Environment": "dev"},
                ],
            }
        )
        tag_filters = {"CostProject": "project-a", "Environment": "dev"}
        result = filter_data_by_tags(data, tag_filters)

        assert len(result) == 1
        assert result["Name"].tolist() == ["instance1"]

    def test_no_match(self):
        """マッチしないテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1", "instance2"],
                "Tags Dict": [
                    {"CostProject": "project-a"},
                    {"CostProject": "project-b"},
                ],
            }
        )
        tag_filters = {"CostProject": "project-c"}
        result = filter_data_by_tags(data, tag_filters)

        assert result.empty

    def test_invalid_tags_dict(self):
        """無効なTags Dictのテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1", "instance2"],
                "Tags Dict": [
                    {"CostProject": "project-a"},
                    "invalid_dict",  # 辞書ではない
                ],
            }
        )
        tag_filters = {"CostProject": "project-a"}
        result = filter_data_by_tags(data, tag_filters)

        assert len(result) == 1
        assert result["Name"].tolist() == ["instance1"]

    def test_missing_tag_key_in_data(self):
        """データにタグキーがない場合のテスト"""
        data = pd.DataFrame(
            {
                "Name": ["instance1", "instance2"],
                "Tags Dict": [
                    {"Environment": "dev"},
                    {"CostProject": "project-a", "Environment": "prod"},
                ],
            }
        )
        tag_filters = {"CostProject": "project-a"}
        result = filter_data_by_tags(data, tag_filters)

        assert len(result) == 1
        assert result["Name"].tolist() == ["instance2"]


class TestRenderTagFilterUI:
    """render_tag_filter_ui関数のテスト"""

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    def test_filter_disabled(
        self, mock_checkbox, mock_subheader, mock_markdown
    ):
        """フィルタが無効な場合のテスト"""
        mock_checkbox.return_value = False

        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }

        result = render_tag_filter_ui(all_data)

        assert result == {}
        mock_checkbox.assert_called_once()

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    @patch("streamlit.sidebar.info")
    @patch("app.web.tag_filter.REQUIRED_TAGS", [])
    def test_no_required_tags(
        self, mock_info, mock_checkbox, mock_subheader, mock_markdown
    ):
        """必須タグが設定されていない場合のテスト"""
        mock_checkbox.return_value = True

        all_data: Dict[str, Any] = {}
        result = render_tag_filter_ui(all_data)

        assert result == {}
        mock_info.assert_called_once_with("必須タグが設定されていません")

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    @patch("streamlit.sidebar.selectbox")
    @patch("app.web.tag_filter.REQUIRED_TAGS", ["CostProject"])
    def test_no_tag_key_selected(
        self, mock_selectbox, mock_checkbox, mock_subheader, mock_markdown
    ):
        """タグキーが選択されていない場合のテスト"""
        mock_checkbox.return_value = True
        mock_selectbox.return_value = ""  # 空文字列を選択

        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }

        result = render_tag_filter_ui(all_data)

        assert result == {}

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    @patch("streamlit.sidebar.selectbox")
    @patch("streamlit.sidebar.warning")
    @patch("app.web.tag_filter.REQUIRED_TAGS", ["CostProject"])
    def test_no_tag_values_available(
        self,
        mock_warning,
        mock_selectbox,
        mock_checkbox,
        mock_subheader,
        mock_markdown,
    ):
        """タグ値が利用できない場合のテスト"""
        mock_checkbox.return_value = True
        mock_selectbox.return_value = "CostProject"

        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [
                        {"Environment": "dev"}
                    ],  # CostProjectタグがない
                }
            )
        }

        result = render_tag_filter_ui(all_data)

        assert result == {}
        mock_warning.assert_called_once_with(
            "'CostProject' に対応する値が見つかりません"
        )

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    @patch("streamlit.sidebar.selectbox")
    @patch("streamlit.sidebar.success")
    @patch("app.web.tag_filter.REQUIRED_TAGS", ["CostProject"])
    def test_successful_filter_selection(
        self,
        mock_success,
        mock_selectbox,
        mock_checkbox,
        mock_subheader,
        mock_markdown,
    ):
        """フィルタ選択が成功した場合のテスト"""
        mock_checkbox.return_value = True
        mock_selectbox.side_effect = ["CostProject", "project-a"]

        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }

        result = render_tag_filter_ui(all_data)

        assert result == {"CostProject": "project-a"}
        mock_success.assert_called_once_with(
            "✅ フィルタ: CostProject=project-a"
        )

    @patch("streamlit.sidebar.markdown")
    @patch("streamlit.sidebar.subheader")
    @patch("streamlit.sidebar.checkbox")
    @patch("streamlit.sidebar.selectbox")
    @patch("app.web.tag_filter.REQUIRED_TAGS", ["CostProject"])
    def test_no_tag_value_selected(
        self, mock_selectbox, mock_checkbox, mock_subheader, mock_markdown
    ):
        """タグ値が選択されていない場合のテスト"""
        mock_checkbox.return_value = True
        mock_selectbox.side_effect = ["CostProject", ""]  # 空文字列を選択

        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }

        result = render_tag_filter_ui(all_data)

        assert result == {}


class TestGetFilteredResourceCount:
    """get_filtered_resource_count関数のテスト"""

    def test_empty_data(self):
        """空のデータのテスト"""
        all_data: Dict[str, Any] = {}
        tag_filters = {"CostProject": "project-a"}
        result = get_filtered_resource_count(all_data, tag_filters)
        assert result == {}

    def test_no_filters(self):
        """フィルタなしのテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2"],
                    "Tags Dict": [
                        {"CostProject": "project-a"},
                        {"CostProject": "project-b"},
                    ],
                }
            )
        }
        tag_filters: Dict[str, Any] = {}
        result = get_filtered_resource_count(all_data, tag_filters)
        assert result == {"EC2": 2}

    def test_with_filters(self):
        """フィルタありのテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2", "instance3"],
                    "Tags Dict": [
                        {"CostProject": "project-a"},
                        {"CostProject": "project-b"},
                        {"CostProject": "project-a"},
                    ],
                }
            ),
            "RDS": pd.DataFrame(
                {"Name": ["db1"], "Tags Dict": [{"CostProject": "project-a"}]}
            ),
        }
        tag_filters = {"CostProject": "project-a"}
        result = get_filtered_resource_count(all_data, tag_filters)
        assert result == {"EC2": 2, "RDS": 1}

    def test_empty_dataframes(self):
        """空のDataFrameがある場合のテスト"""
        all_data = {
            "EC2": pd.DataFrame(),
            "RDS": pd.DataFrame(
                {"Name": ["db1"], "Tags Dict": [{"CostProject": "project-a"}]}
            ),
        }
        tag_filters = {"CostProject": "project-a"}
        result = get_filtered_resource_count(all_data, tag_filters)
        assert result == {"EC2": 0, "RDS": 1}

    def test_no_matches(self):
        """マッチしない場合のテスト"""
        all_data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }
        tag_filters = {"CostProject": "project-b"}
        result = get_filtered_resource_count(all_data, tag_filters)
        assert result == {"EC2": 0}
