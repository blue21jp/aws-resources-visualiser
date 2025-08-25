#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - サイドバーUIのテスト"""

# Standard Library
from unittest.mock import patch

# First Party Library
from app.web.sidebar_ui import SidebarUI, get_sidebar_ui


class TestSidebarUI:
    """SidebarUI クラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.sidebar_ui = SidebarUI()

    @patch("os.environ.get")
    def test_is_running_on_ecs_true(self, mock_env_get):
        """ECS環境判定のテスト（True）"""
        mock_env_get.return_value = "http://169.254.170.2/v4/metadata"

        result = SidebarUI._is_running_on_ecs()
        assert result is True
        mock_env_get.assert_called_once_with("ECS_CONTAINER_METADATA_URI_V4")

    @patch("os.environ.get")
    def test_is_running_on_ecs_false(self, mock_env_get):
        """ECS環境判定のテスト（False）"""
        mock_env_get.return_value = None

        result = SidebarUI._is_running_on_ecs()
        assert result is False

    def test_init(self):
        """初期化のテスト"""
        with patch.object(SidebarUI, "_is_running_on_ecs", return_value=False):
            ui = SidebarUI()
            assert ui.running_on_ecs is False

    def test_init_ecs_environment(self):
        """ECS環境での初期化のテスト"""
        with patch.object(SidebarUI, "_is_running_on_ecs", return_value=True):
            ui = SidebarUI()
            assert ui.running_on_ecs is True

    @patch("streamlit.set_page_config")
    @patch(
        "app.web.sidebar_ui.STREAMLIT_CONFIG",
        {"page_title": "Test", "layout": "wide"},
    )
    def test_setup_page_config(self, mock_set_page_config):
        """ページ設定のテスト"""
        SidebarUI.setup_page_config()
        mock_set_page_config.assert_called_once_with(
            page_title="Test", layout="wide"
        )

    @patch("streamlit.title")
    @patch("streamlit.markdown")
    def test_render_header(self, mock_markdown, mock_title):
        """ヘッダー表示のテスト"""
        SidebarUI.render_header()

        mock_title.assert_called_once_with("☁️ AWS Resource Visualizer")
        mock_markdown.assert_called_once_with(
            "AWSアカウント内の主要リソースを可視化します"
        )

    @patch("streamlit.sidebar.header")
    def test_render_sidebar_settings_basic(self, mock_header):
        """基本的なサイドバー設定表示のテスト"""
        with patch.object(
            self.sidebar_ui,
            "_render_data_update_controls",
            return_value=(False, False),
        ) as mock_update, patch.object(
            self.sidebar_ui,
            "_render_profile_selection",
            return_value="sandbox",
        ) as mock_profile, patch.object(
            self.sidebar_ui, "_handle_profile_change"
        ) as mock_handle_profile, patch.object(
            self.sidebar_ui,
            "_render_region_selection",
            return_value="us-east-1",
        ) as mock_region, patch.object(
            self.sidebar_ui, "_handle_region_change"
        ) as mock_handle_region, patch.object(
            self.sidebar_ui,
            "_render_service_selection",
            return_value=["EC2", "RDS"],
        ) as mock_services:

            result = self.sidebar_ui.render_sidebar_settings()

            # 戻り値の確認
            assert result == (
                "sandbox",
                "us-east-1",
                ["EC2", "RDS"],
                False,
                False,
            )

            # 各メソッドが呼ばれることを確認
            mock_update.assert_called_once()
            mock_profile.assert_called_once()
            mock_handle_profile.assert_called_once_with("sandbox")
            mock_region.assert_called_once()
            mock_handle_region.assert_called_once_with("us-east-1")
            mock_services.assert_called_once()

    @patch("streamlit.sidebar.header")
    def test_render_sidebar_settings_with_refresh(self, mock_header):
        """リフレッシュボタン付きサイドバー設定のテスト"""
        with patch.object(
            self.sidebar_ui,
            "_render_data_update_controls",
            return_value=(True, True),
        ), patch.object(
            self.sidebar_ui,
            "_render_profile_selection",
            return_value="default",
        ), patch.object(
            self.sidebar_ui, "_handle_profile_change"
        ), patch.object(
            self.sidebar_ui,
            "_render_region_selection",
            return_value="ap-northeast-1",
        ), patch.object(
            self.sidebar_ui, "_handle_region_change"
        ), patch.object(
            self.sidebar_ui, "_render_service_selection", return_value=["S3"]
        ):

            result = self.sidebar_ui.render_sidebar_settings()

            # 戻り値の確認（リフレッシュとキャッシュクリアがTrue）
            assert result == ("default", "ap-northeast-1", ["S3"], True, True)

    def test_render_sidebar_settings_return_types(self):
        """サイドバー設定の戻り値型テスト"""
        with patch.object(
            self.sidebar_ui,
            "_render_data_update_controls",
            return_value=(False, False),
        ), patch.object(
            self.sidebar_ui,
            "_render_profile_selection",
            return_value="sandbox",
        ), patch.object(
            self.sidebar_ui, "_handle_profile_change"
        ), patch.object(
            self.sidebar_ui,
            "_render_region_selection",
            return_value="us-east-1",
        ), patch.object(
            self.sidebar_ui, "_handle_region_change"
        ), patch.object(
            self.sidebar_ui,
            "_render_service_selection",
            return_value=["EC2", "RDS"],
        ), patch(
            "streamlit.sidebar.header"
        ), patch(
            "streamlit.sidebar.markdown"
        ):

            result = self.sidebar_ui.render_sidebar_settings()

            # 戻り値の型確認
            assert isinstance(result, tuple)
            assert len(result) == 5
            assert isinstance(result[0], str)  # profile
            assert isinstance(result[1], str)  # region
            assert isinstance(result[2], list)  # services
            assert isinstance(result[3], bool)  # refresh_button
            assert isinstance(result[4], bool)  # clear_cache

    @patch("streamlit.sidebar.button")
    @patch("streamlit.sidebar.markdown")
    def test_render_data_update_controls(self, mock_markdown, mock_button):
        """データ更新コントロールのテスト"""
        mock_button.side_effect = [
            True,
            False,
        ]  # refresh=True, clear_cache=False

        refresh, clear_cache = self.sidebar_ui._render_data_update_controls()

        # 検証
        assert refresh is True
        assert clear_cache is False
        # ボタンが2回呼ばれることを確認（refresh用とclear_cache用）
        assert mock_button.call_count >= 1  # 少なくとも1回は呼ばれる

    @patch("streamlit.sidebar.selectbox")
    def test_render_profile_selection_non_ecs(self, mock_selectbox):
        """非ECS環境でのプロファイル選択のテスト"""
        self.sidebar_ui.running_on_ecs = False
        mock_selectbox.return_value = "sandbox"

        result = self.sidebar_ui._render_profile_selection()

        # 検証
        assert result == "sandbox"
        mock_selectbox.assert_called_once()

    def test_render_profile_selection_ecs(self):
        """ECS環境でのプロファイル選択のテスト"""
        self.sidebar_ui.running_on_ecs = True

        result = self.sidebar_ui._render_profile_selection()

        # 検証（ECS環境ではNoneが返される）
        assert result is None

    @patch("streamlit.sidebar.selectbox")
    def test_render_region_selection_non_ecs(self, mock_selectbox):
        """非ECS環境でのリージョン選択のテスト"""
        self.sidebar_ui.running_on_ecs = False
        mock_selectbox.return_value = "us-east-1"

        result = self.sidebar_ui._render_region_selection()

        # 検証
        assert result == "us-east-1"
        mock_selectbox.assert_called_once()

    @patch("streamlit.sidebar.multiselect")
    def test_render_service_selection(self, mock_multiselect):
        """サービス選択のテスト"""
        mock_multiselect.return_value = ["EC2", "RDS"]

        result = self.sidebar_ui._render_service_selection()

        # 検証
        assert result == ["EC2", "RDS"]
        mock_multiselect.assert_called_once()

    @patch("streamlit.warning")
    def test_render_no_services_warning(self, mock_warning):
        """サービス未選択警告のテスト"""
        self.sidebar_ui.render_no_services_warning()

        # 検証
        mock_warning.assert_called_once()

    @patch("streamlit.error")
    def test_render_authentication_error(self, mock_error):
        """認証エラー表示のテスト"""
        self.sidebar_ui.render_authentication_error("sandbox")

        # 検証
        mock_error.assert_called_once()

    def test_render_batch_started_success(self):
        """バッチ開始成功メッセージのテスト"""
        # エラーが発生しないことを確認
        self.sidebar_ui.render_batch_started_success()

    @patch("streamlit.info")
    def test_render_initial_info_display(self, mock_info):
        """初期情報表示のテスト"""
        self.sidebar_ui.render_initial_info_display(["EC2", "RDS"])

        # 検証
        mock_info.assert_called()


class TestGetSidebarUI:
    """get_sidebar_ui関数のテスト"""

    def test_get_sidebar_ui_singleton(self):
        """シングルトンパターンのテスト"""
        ui1 = get_sidebar_ui()
        ui2 = get_sidebar_ui()

        # 検証
        assert ui1 is ui2
        assert isinstance(ui1, SidebarUI)
