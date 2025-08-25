#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""設定モジュールのテスト"""

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# First Party Library
from app.shared import config


class TestConfig:
    """設定モジュールのテストクラス"""

    def test_supported_regions(self):
        """サポートリージョンの設定テスト"""
        assert isinstance(config.SUPPORTED_REGIONS, list)
        assert len(config.SUPPORTED_REGIONS) > 0
        assert "us-east-1" in config.SUPPORTED_REGIONS
        assert "ap-northeast-1" in config.SUPPORTED_REGIONS

    def test_supported_services(self):
        """サポートサービスの設定テスト"""
        assert isinstance(config.SUPPORTED_SERVICES, dict)
        assert len(config.SUPPORTED_SERVICES) > 0

        expected_services = ["EC2", "RDS", "S3", "Lambda"]
        for service in expected_services:
            assert service in config.SUPPORTED_SERVICES
            assert isinstance(config.SUPPORTED_SERVICES[service], str)
            assert len(config.SUPPORTED_SERVICES[service]) > 0

    def test_required_tags(self):
        """必須タグの設定テスト"""
        assert isinstance(config.REQUIRED_TAGS, list)
        assert len(config.REQUIRED_TAGS) > 0
        assert "CostProject" in config.REQUIRED_TAGS

    def test_chart_colors(self):
        """チャート色の設定テスト"""
        assert isinstance(config.CHART_COLORS, dict)
        assert "success" in config.CHART_COLORS
        assert "danger" in config.CHART_COLORS
        assert config.CHART_COLORS["success"].startswith("#")
        assert config.CHART_COLORS["danger"].startswith("#")

    def test_streamlit_config(self):
        """Streamlit設定のテスト"""
        assert isinstance(config.STREAMLIT_CONFIG, dict)

        required_keys = [
            "page_title",
            "page_icon",
            "layout",
            "initial_sidebar_state",
        ]
        for key in required_keys:
            assert key in config.STREAMLIT_CONFIG
            assert config.STREAMLIT_CONFIG[key] is not None

    def test_cache_settings(self):
        """キャッシュ設定のテスト"""
        assert isinstance(config.CACHE_TTL, int)
        assert config.CACHE_TTL > 0

        assert isinstance(config.CACHE_DIR, str)
        assert len(config.CACHE_DIR) > 0
        # プロジェクトルート基準のパスであることを確認
        assert "cache" in config.CACHE_DIR
        assert Path(config.CACHE_DIR).is_absolute()

    def test_estimated_costs(self):
        """概算コストの設定テスト"""
        assert isinstance(config.ESTIMATED_COSTS, dict)

        for service in config.SUPPORTED_SERVICES.keys():
            assert service in config.ESTIMATED_COSTS
            assert isinstance(config.ESTIMATED_COSTS[service], (int, float))
            assert config.ESTIMATED_COSTS[service] > 0

    def test_cost_calculation_info(self):
        """コスト計算情報の設定テスト"""
        assert isinstance(config.COST_CALCULATION_INFO, dict)

        for service in config.SUPPORTED_SERVICES.keys():
            assert service in config.COST_CALCULATION_INFO
            assert isinstance(config.COST_CALCULATION_INFO[service], str)
            assert len(config.COST_CALCULATION_INFO[service]) > 0

    def test_cost_disclaimer(self):
        """コスト免責事項の設定テスト"""
        assert isinstance(config.COST_DISCLAIMER, str)
        assert len(config.COST_DISCLAIMER) > 0
        assert "概算コスト" in config.COST_DISCLAIMER
        assert "AWS Pricing Calculator" in config.COST_DISCLAIMER

    def test_pagination_config(self):
        """ページネーション設定のテスト"""
        assert isinstance(config.PAGINATION_CONFIG, dict)

        required_keys = [
            "default_page_size",
            "page_size_options",
            "show_page_info",
            "show_total_count",
        ]
        for key in required_keys:
            assert key in config.PAGINATION_CONFIG

        assert isinstance(config.PAGINATION_CONFIG["default_page_size"], int)
        assert config.PAGINATION_CONFIG["default_page_size"] > 0

        assert isinstance(config.PAGINATION_CONFIG["page_size_options"], list)
        assert len(config.PAGINATION_CONFIG["page_size_options"]) > 0
        assert all(
            isinstance(size, int) and size > 0
            for size in config.PAGINATION_CONFIG["page_size_options"]
        )

    def test_default_values(self):
        """デフォルト値の設定テスト"""
        assert isinstance(config.DEFAULT_REGION, str)
        assert config.DEFAULT_REGION in config.SUPPORTED_REGIONS

        assert isinstance(config.DEFAULT_SERVICES, list)
        assert len(config.DEFAULT_SERVICES) > 0
        assert all(
            service in config.SUPPORTED_SERVICES
            for service in config.DEFAULT_SERVICES
        )

        assert isinstance(config.AVAILABLE_PROFILES, list)
        assert len(config.AVAILABLE_PROFILES) > 0

        assert isinstance(config.DEFAULT_PROFILE, str)
        assert config.DEFAULT_PROFILE in config.AVAILABLE_PROFILES

    @pytest.mark.parametrize(
        "service,expected_cost",
        [
            ("EC2", 50.0),
            ("RDS", 100.0),
            ("S3", 5.0),
            ("Lambda", 1.0),
        ],
    )
    def test_service_costs(self, service: str, expected_cost: float):
        """サービス別コスト設定のテスト"""
        assert config.ESTIMATED_COSTS[service] == expected_cost

    @pytest.mark.parametrize("page_size", [5, 10, 20, 50, 100])
    def test_pagination_page_sizes(self, page_size: int):
        """ページネーションサイズオプションのテスト"""
        assert page_size in config.PAGINATION_CONFIG["page_size_options"]

    def test_config_consistency(self):
        """設定の整合性テスト"""
        # サポートサービスと概算コストの整合性
        assert set(config.SUPPORTED_SERVICES.keys()) == set(
            config.ESTIMATED_COSTS.keys()
        )

        # サポートサービスとコスト計算情報の整合性
        assert set(config.SUPPORTED_SERVICES.keys()) == set(
            config.COST_CALCULATION_INFO.keys()
        )

        # デフォルトサービスがサポートサービスに含まれているか
        assert all(
            service in config.SUPPORTED_SERVICES
            for service in config.DEFAULT_SERVICES
        )

        # デフォルトリージョンがサポートリージョンに含まれているか
        assert config.DEFAULT_REGION in config.SUPPORTED_REGIONS

        # デフォルトプロファイルが利用可能プロファイルに含まれているか
        assert config.DEFAULT_PROFILE in config.AVAILABLE_PROFILES


class TestConfigFunctions:
    """設定関数のテストクラス"""

    def test_get_effective_region_ecs_environment(self, monkeypatch):
        """ECS環境でのget_effective_region関数のテスト"""
        # ECS環境をシミュレート
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "ecs")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")

        result = config.get_effective_region("ap-northeast-1")
        assert result == "us-west-2"

    def test_get_effective_region_ecs_environment_no_env_var(
        self, monkeypatch
    ):
        """ECS環境で環境変数がない場合のget_effective_region関数のテスト"""
        # ECS環境をシミュレート、環境変数なし
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "ecs")
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

        result = config.get_effective_region("ap-northeast-1")
        assert result == config.DEFAULT_REGION

    def test_get_effective_region_non_ecs_environment(self, monkeypatch):
        """非ECS環境でのget_effective_region関数のテスト"""
        # Poetry環境をシミュレート
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.get_effective_region("ap-northeast-1")
        assert result == "ap-northeast-1"

    def test_get_effective_profile_ecs_environment(self, monkeypatch):
        """ECS環境でのget_effective_profile関数のテスト"""
        # ECS環境をシミュレート
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "ecs")

        result = config.get_effective_profile("sandbox")
        assert result is None

    def test_get_effective_profile_non_ecs_environment(self, monkeypatch):
        """非ECS環境でのget_effective_profile関数のテスト"""
        # Poetry環境をシミュレート
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.get_effective_profile("sandbox")
        assert result == "sandbox"

    def test_get_effective_profile_none_input(self, monkeypatch):
        """プロファイルがNoneの場合のget_effective_profile関数のテスト"""
        # Poetry環境をシミュレート
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.get_effective_profile(None)
        assert result is None

    def test_should_use_profile_in_command_poetry_with_profile(
        self, monkeypatch
    ):
        """Poetry環境でプロファイル指定ありの場合のshould_use_profile_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.should_use_profile_in_command("sandbox")
        assert result is True

    def test_should_use_profile_in_command_docker_with_profile(
        self, monkeypatch
    ):
        """Docker環境でプロファイル指定ありの場合のshould_use_profile_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "docker")

        result = config.should_use_profile_in_command("sandbox")
        assert result is True

    def test_should_use_profile_in_command_ecs_with_profile(self, monkeypatch):
        """ECS環境でプロファイル指定ありの場合のshould_use_profile_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "ecs")

        result = config.should_use_profile_in_command("sandbox")
        assert result is False

    def test_should_use_profile_in_command_poetry_without_profile(
        self, monkeypatch
    ):
        """Poetry環境でプロファイル指定なしの場合のshould_use_profile_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.should_use_profile_in_command(None)
        assert result is False

    def test_should_use_region_in_command_poetry(self, monkeypatch):
        """Poetry環境でのshould_use_region_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "poetry")

        result = config.should_use_region_in_command()
        assert result is True

    def test_should_use_region_in_command_docker(self, monkeypatch):
        """Docker環境でのshould_use_region_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "docker")

        result = config.should_use_region_in_command()
        assert result is True

    def test_should_use_region_in_command_ecs(self, monkeypatch):
        """ECS環境でのshould_use_region_in_command関数のテスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", "ecs")

        result = config.should_use_region_in_command()
        assert result is False

    @pytest.mark.parametrize(
        "batch_run_type,expected",
        [
            ("poetry", True),
            ("docker", True),
            ("ecs", False),
            ("unknown", False),
        ],
    )
    def test_should_use_region_in_command_parametrized(
        self, monkeypatch, batch_run_type: str, expected: bool
    ):
        """should_use_region_in_command関数のパラメータ化テスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", batch_run_type)

        result = config.should_use_region_in_command()
        assert result is expected

    @pytest.mark.parametrize(
        "batch_run_type,profile,expected",
        [
            ("poetry", "sandbox", True),
            ("docker", "sandbox", True),
            ("ecs", "sandbox", False),
            ("poetry", None, False),
            ("docker", None, False),
            ("ecs", None, False),
            ("unknown", "sandbox", False),
        ],
    )
    def test_should_use_profile_in_command_parametrized(
        self, monkeypatch, batch_run_type: str, profile: str, expected: bool
    ):
        """should_use_profile_in_command関数のパラメータ化テスト"""
        monkeypatch.setattr(config, "BATCH_RUN_TYPE", batch_run_type)

        result = config.should_use_profile_in_command(profile)
        assert result is expected
