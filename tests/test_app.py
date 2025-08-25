#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - メインアプリケーションのテスト"""

# Standard Library
from unittest.mock import MagicMock, patch

# First Party Library
from app.web.app import main, validate_aws_authentication


class TestValidateAwsAuthentication:
    """validate_aws_authentication関数のテスト"""

    @patch("boto3.Session")
    def test_valid_authentication_default_profile(self, mock_session):
        """デフォルトプロファイルでの有効な認証テスト"""
        # モック設定
        mock_session_instance = MagicMock()
        mock_credentials = MagicMock()
        mock_session_instance.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_session_instance

        result = validate_aws_authentication("default")

        assert result is True
        mock_session.assert_called_once_with(profile_name=None)

    @patch("boto3.Session")
    def test_valid_authentication_custom_profile(self, mock_session):
        """カスタムプロファイルでの有効な認証テスト"""
        # モック設定
        mock_session_instance = MagicMock()
        mock_credentials = MagicMock()
        mock_session_instance.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_session_instance

        result = validate_aws_authentication("sandbox")

        assert result is True
        mock_session.assert_called_once_with(profile_name="sandbox")

    @patch("boto3.Session")
    def test_invalid_authentication_no_credentials(self, mock_session):
        """認証情報がない場合のテスト"""
        # モック設定
        mock_session_instance = MagicMock()
        mock_session_instance.get_credentials.return_value = None
        mock_session.return_value = mock_session_instance

        result = validate_aws_authentication("test")

        assert result is False

    @patch("boto3.Session")
    def test_invalid_authentication_exception(self, mock_session):
        """例外が発生した場合のテスト"""
        # モック設定
        mock_session.side_effect = Exception("Profile not found")

        result = validate_aws_authentication("invalid")

        assert result is False

    @patch("boto3.Session")
    def test_none_profile(self, mock_session):
        """Noneプロファイルのテスト"""
        # モック設定
        mock_session_instance = MagicMock()
        mock_credentials = MagicMock()
        mock_session_instance.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_session_instance

        result = validate_aws_authentication(None)

        assert result is True
        mock_session.assert_called_once_with(profile_name=None)


class TestMain:
    """main関数のテスト"""

    @patch("app.web.app.get_sidebar_ui")
    @patch("app.web.app.get_main_content_ui")
    @patch("app.web.app.get_state_manager")
    @patch("app.web.app.get_batch_processor")
    @patch("app.web.app._handle_settings_change")
    @patch("app.web.app._check_initial_status")
    @patch("streamlit.title")
    def test_main_basic_flow(
        self,
        mock_st_title,
        mock_check_initial_status,
        mock_handle_settings_change,
        mock_get_batch_processor,
        mock_get_state_manager,
        mock_get_main_content_ui,
        mock_get_sidebar_ui,
    ):
        """main関数の基本フローテスト"""
        # モック設定
        mock_sidebar_ui = MagicMock()
        mock_main_content_ui = MagicMock()
        mock_state_manager = MagicMock()
        mock_batch_processor = MagicMock()

        mock_get_sidebar_ui.return_value = mock_sidebar_ui
        mock_get_main_content_ui.return_value = mock_main_content_ui
        mock_get_state_manager.return_value = mock_state_manager
        mock_get_batch_processor.return_value = mock_batch_processor

        # サイドバーUIの戻り値設定
        mock_sidebar_ui.render_sidebar_settings.return_value = (
            "sandbox",  # selected_profile
            "us-east-1",  # selected_region
            ["EC2", "RDS"],  # selected_services
            False,  # refresh_button
            False,  # clear_cache
        )

        # main関数実行
        main()

        # 初期化メソッドが呼ばれることを確認
        mock_sidebar_ui.setup_page_config.assert_called_once()
        mock_sidebar_ui.render_header.assert_called_once()
        mock_sidebar_ui.render_sidebar_settings.assert_called_once()

        # タイトルが表示されることを確認
        mock_st_title.assert_called_once_with(
            "sandbox(us-east-1)のリソース情報"
        )

        # 設定変更処理が呼ばれることを確認
        mock_handle_settings_change.assert_called_once_with(
            "sandbox",
            "us-east-1",
            ["EC2", "RDS"],
            mock_state_manager,
            mock_batch_processor,
        )

        # 初期状態チェックが呼ばれることを確認
        mock_check_initial_status.assert_called_once_with(
            ["EC2", "RDS"],
            "us-east-1",
            "sandbox",
            mock_batch_processor,
            mock_state_manager,
        )

    @patch("app.web.app.get_sidebar_ui")
    @patch("app.web.app.get_main_content_ui")
    @patch("app.web.app.get_state_manager")
    @patch("app.web.app.get_batch_processor")
    def test_main_no_services_selected(
        self,
        mock_get_batch_processor,
        mock_get_state_manager,
        mock_get_main_content_ui,
        mock_get_sidebar_ui,
    ):
        """サービス未選択時のmain関数テスト"""
        # モック設定
        mock_sidebar_ui = MagicMock()
        mock_main_content_ui = MagicMock()
        mock_state_manager = MagicMock()
        mock_batch_processor = MagicMock()

        mock_get_sidebar_ui.return_value = mock_sidebar_ui
        mock_get_main_content_ui.return_value = mock_main_content_ui
        mock_get_state_manager.return_value = mock_state_manager
        mock_get_batch_processor.return_value = mock_batch_processor

        # サイドバーUIの戻り値設定（サービス未選択）
        mock_sidebar_ui.render_sidebar_settings.return_value = (
            "sandbox",  # selected_profile
            "us-east-1",  # selected_region
            [],  # selected_services (空)
            False,  # refresh_button
            False,  # clear_cache
        )

        # main関数実行
        main()

        # 警告メッセージが表示されることを確認
        mock_sidebar_ui.render_no_services_warning.assert_called_once()

    @patch("app.web.app.get_sidebar_ui")
    @patch("app.web.app.get_main_content_ui")
    @patch("app.web.app.get_state_manager")
    @patch("app.web.app.get_batch_processor")
    @patch("app.web.app._handle_settings_change")
    @patch("app.web.app._check_initial_status")
    @patch("streamlit.title")
    def test_main_with_refresh_and_clear_cache(
        self,
        mock_st_title,
        mock_check_initial_status,
        mock_handle_settings_change,
        mock_get_batch_processor,
        mock_get_state_manager,
        mock_get_main_content_ui,
        mock_get_sidebar_ui,
    ):
        """リフレッシュとキャッシュクリア付きのmain関数テスト"""
        # モック設定
        mock_sidebar_ui = MagicMock()
        mock_main_content_ui = MagicMock()
        mock_state_manager = MagicMock()
        mock_batch_processor = MagicMock()

        mock_get_sidebar_ui.return_value = mock_sidebar_ui
        mock_get_main_content_ui.return_value = mock_main_content_ui
        mock_get_state_manager.return_value = mock_state_manager
        mock_get_batch_processor.return_value = mock_batch_processor

        # サイドバーUIの戻り値設定
        mock_sidebar_ui.render_sidebar_settings.return_value = (
            "production",  # selected_profile
            "ap-northeast-1",  # selected_region
            ["S3", "Lambda"],  # selected_services
            True,  # refresh_button
            True,  # clear_cache
        )

        # main関数実行
        main()

        # 正しいパラメータで処理が呼ばれることを確認
        mock_st_title.assert_called_once_with(
            "production(ap-northeast-1)のリソース情報"
        )
        mock_handle_settings_change.assert_called_once_with(
            "production",
            "ap-northeast-1",
            ["S3", "Lambda"],
            mock_state_manager,
            mock_batch_processor,
        )
        mock_check_initial_status.assert_called_once_with(
            ["S3", "Lambda"],
            "ap-northeast-1",
            "production",
            mock_batch_processor,
            mock_state_manager,
        )

    def test_main_instance_creation(self):
        """main関数でのインスタンス作成テスト"""
        with patch("app.web.app.get_sidebar_ui") as mock_get_sidebar_ui, patch(
            "app.web.app.get_main_content_ui"
        ) as mock_get_main_content_ui, patch(
            "app.web.app.get_state_manager"
        ) as mock_get_state_manager, patch(
            "app.web.app.get_batch_processor"
        ) as mock_get_batch_processor, patch(
            "app.web.app._handle_settings_change"
        ), patch(
            "app.web.app._check_initial_status"
        ), patch(
            "streamlit.header"
        ):

            # 各インスタンス取得関数のモック設定
            mock_sidebar_ui = MagicMock()
            mock_main_content_ui = MagicMock()
            mock_state_manager = MagicMock()
            mock_batch_processor = MagicMock()

            mock_get_sidebar_ui.return_value = mock_sidebar_ui
            mock_get_main_content_ui.return_value = mock_main_content_ui
            mock_get_state_manager.return_value = mock_state_manager
            mock_get_batch_processor.return_value = mock_batch_processor

            mock_sidebar_ui.render_sidebar_settings.return_value = (
                "test",
                "us-east-1",
                ["EC2"],
                False,
                False,
            )

            # main関数実行
            main()

            # 各インスタンス取得関数が呼ばれることを確認
            mock_get_sidebar_ui.assert_called_once()
            mock_get_main_content_ui.assert_called_once()
            mock_get_state_manager.assert_called_once()
            mock_get_batch_processor.assert_called_once()
