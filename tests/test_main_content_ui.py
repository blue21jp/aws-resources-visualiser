#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - メインコンテンツUIのテスト"""

# Standard Library
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Third Party Library
import pandas as pd

# First Party Library
from app.web.main_content_ui import MainContentUI


class TestMainContentUI:
    """MainContentUI クラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.main_content_ui = MainContentUI()

    @patch("streamlit.info")
    @patch("streamlit.tabs")
    @patch("app.web.main_content_ui.get_filtered_resource_count")
    def test_render_data_tabs_with_filters(
        self, mock_get_filtered_count, mock_tabs, mock_st_info
    ):
        """フィルタ付きデータタブ表示のテスト"""
        # モック設定
        mock_get_filtered_count.return_value = {"EC2": 2, "RDS": 1}
        mock_tabs.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]  # EC2, RDS, 可視化

        # テストデータ
        selected_services = ["EC2", "RDS"]
        selected_region = "us-east-1"
        tag_filters = {"CostProject": "project-a"}
        data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2", "instance3"],
                    "Tags Dict": [
                        {"CostProject": "project-a"},
                        {"CostProject": "project-a"},
                        {"CostProject": "project-b"},
                    ],
                }
            ),
            "RDS": pd.DataFrame(
                {
                    "Name": ["db1", "db2"],
                    "Tags Dict": [
                        {"CostProject": "project-a"},
                        {"CostProject": "project-b"},
                    ],
                }
            ),
        }

        with patch.object(
            self.main_content_ui, "_render_service_data_tab"
        ) as mock_render_service, patch.object(
            self.main_content_ui, "_render_visualization_tab"
        ) as mock_render_viz:

            self.main_content_ui.render_data_tabs(
                selected_services, selected_region, tag_filters, data
            )

        # フィルタ情報が表示されることを確認
        mock_st_info.assert_called_once()
        mock_get_filtered_count.assert_called_once_with(data, tag_filters)

        # タブが作成されることを確認
        mock_tabs.assert_called_once_with(["EC2", "RDS", "📈 可視化"])

        # 各サービスタブが呼ばれることを確認
        assert mock_render_service.call_count == 2
        mock_render_viz.assert_called_once()

    @patch("streamlit.tabs")
    @patch("app.web.main_content_ui.get_filtered_resource_count")
    def test_render_data_tabs_without_filters(
        self, mock_get_filtered_count, mock_tabs
    ):
        """フィルタなしデータタブ表示のテスト"""
        # モック設定
        mock_tabs.return_value = [MagicMock(), MagicMock()]  # EC2, 可視化

        # テストデータ
        selected_services = ["EC2"]
        selected_region = "us-east-1"
        tag_filters: Dict[str, Any] = {}
        data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1"],
                    "Tags Dict": [{"CostProject": "project-a"}],
                }
            )
        }

        with patch.object(
            self.main_content_ui, "_render_service_data_tab"
        ), patch.object(self.main_content_ui, "_render_visualization_tab"):

            self.main_content_ui.render_data_tabs(
                selected_services, selected_region, tag_filters, data
            )

        # フィルタ情報が表示されないことを確認
        mock_get_filtered_count.assert_not_called()

        # タブが作成されることを確認
        mock_tabs.assert_called_once_with(["EC2", "📈 可視化"])

    def test_init(self):
        """初期化のテスト"""
        ui = MainContentUI()
        assert isinstance(ui, MainContentUI)

    @patch("streamlit.tabs")
    def test_render_data_tabs_empty_data(self, mock_tabs):
        """空データでのテスト"""
        mock_tabs.return_value = [MagicMock(), MagicMock()]

        selected_services = ["EC2"]
        selected_region = "us-east-1"
        tag_filters: Dict[str, Any] = {}
        data = {"EC2": pd.DataFrame()}

        with patch.object(
            self.main_content_ui, "_render_service_data_tab"
        ) as mock_render_service, patch.object(
            self.main_content_ui, "_render_visualization_tab"
        ) as mock_render_viz:

            self.main_content_ui.render_data_tabs(
                selected_services, selected_region, tag_filters, data
            )

        # エラーが発生しないことを確認
        mock_render_service.assert_called_once()
        mock_render_viz.assert_called_once()

    @patch("streamlit.info")
    @patch("streamlit.tabs")
    @patch("app.web.main_content_ui.get_filtered_resource_count")
    def test_render_data_tabs_filter_calculation(
        self, mock_get_filtered_count, mock_tabs, mock_st_info
    ):
        """フィルタ計算のテスト"""
        # モック設定
        mock_get_filtered_count.return_value = {"EC2": 1, "RDS": 0}
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]

        # テストデータ
        selected_services = ["EC2", "RDS"]
        selected_region = "us-east-1"
        tag_filters = {"CostProject": "project-a"}
        data = {
            "EC2": pd.DataFrame({"Name": ["instance1", "instance2"]}),
            "RDS": pd.DataFrame({"Name": ["db1", "db2", "db3"]}),
        }

        with patch.object(
            self.main_content_ui, "_render_service_data_tab"
        ), patch.object(self.main_content_ui, "_render_visualization_tab"):

            self.main_content_ui.render_data_tabs(
                selected_services, selected_region, tag_filters, data
            )

        # 正しい計算結果でinfo表示されることを確認
        call_args = mock_st_info.call_args[0][0]
        assert "1/5" in call_args  # フィルタ結果/全体
        assert "必須タグフィルタ適用中" in call_args

    @patch("streamlit.tabs")
    def test_render_data_tabs_single_service(self, mock_tabs):
        """単一サービスのテスト"""
        mock_tabs.return_value = [MagicMock(), MagicMock()]  # S3, 可視化

        selected_services = ["S3"]
        selected_region = "us-east-1"
        tag_filters: Dict[str, Any] = {}
        data = {"S3": pd.DataFrame({"Name": ["bucket1"]})}

        with patch.object(
            self.main_content_ui, "_render_service_data_tab"
        ) as mock_render_service, patch.object(
            self.main_content_ui, "_render_visualization_tab"
        ) as mock_render_viz:

            self.main_content_ui.render_data_tabs(
                selected_services, selected_region, tag_filters, data
            )

        # タブが正しく作成されることを確認
        mock_tabs.assert_called_once_with(["S3", "📈 可視化"])
        mock_render_service.assert_called_once()
        mock_render_viz.assert_called_once()

    @patch("streamlit.subheader")
    @patch("streamlit.info")
    @patch("streamlit.columns")
    @patch("streamlit.selectbox")
    @patch("streamlit.dataframe")
    @patch("app.web.main_content_ui.paginate_dataframe")
    @patch("app.web.main_content_ui.render_pagination_info")
    @patch("app.web.main_content_ui.render_pagination_controls")
    def test_render_service_data_tab_with_data(
        self,
        mock_render_controls,
        mock_render_info,
        mock_paginate,
        mock_dataframe,
        mock_selectbox,
        mock_columns,
        mock_info,
        mock_subheader,
    ):
        """データありサービスタブのテスト"""
        # モック設定
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_selectbox.return_value = 10

        # ページネーション結果のモック
        paginated_data = pd.DataFrame(
            {"Name": ["instance1"], "Required Tags": ["CostProject: test"]}
        )
        pagination_info = {"total_pages": 2, "current_page": 1}
        mock_paginate.return_value = (paginated_data, pagination_info)

        # テストデータ
        service = "EC2"
        region = "us-east-1"
        tag_filters: Dict[str, Any] = {}
        data = {
            "EC2": pd.DataFrame(
                {
                    "Name": ["instance1", "instance2"],
                    "Required Tags": ["CostProject: test", ""],
                    "Tags Dict": [{"CostProject": "test"}, {}],
                }
            )
        }

        # テスト実行
        self.main_content_ui._render_service_data_tab(
            service, region, tag_filters, data
        )

        # 検証
        mock_subheader.assert_called_once_with("EC2 リソース一覧")
        mock_paginate.assert_called_once()
        mock_render_info.assert_called_once()
        mock_render_controls.assert_called()  # 複数回呼ばれる可能性
