#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""キャッシュマネージャーのテスト"""

# Standard Library

# Third Party Library
import pandas as pd
import pytest

# First Party Library
from app.shared.cache_manager import PersistentCache, get_cache_instance


class TestPersistentCache:
    """PersistentCacheクラスのテストクラス"""

    def test_init_creates_cache_directory(self, temp_cache_dir):
        """キャッシュディレクトリが作成されることをテスト"""
        cache = PersistentCache(temp_cache_dir)
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()

    def test_get_cache_key(self, temp_cache_dir):
        """キャッシュキー生成のテスト"""
        cache = PersistentCache(temp_cache_dir)

        # プロファイル指定あり
        key1 = cache.get_cache_key("EC2", "us-east-1", "sandbox")
        assert key1 == "EC2_us-east-1_sandbox"

        # プロファイル指定なし
        key2 = cache.get_cache_key("RDS", "ap-northeast-1", None)
        assert key2 == "RDS_ap-northeast-1_default"

    def test_get_cached_data_not_exists(self, temp_cache_dir):
        """存在しないキャッシュの取得テスト"""
        cache = PersistentCache(temp_cache_dir)

        result = cache.get_cached_data("EC2", "us-east-1", "sandbox")
        assert result is None

    def test_cache_basic_operations(self, temp_cache_dir, sample_aws_data):
        """基本的なキャッシュ操作のテスト"""
        cache = PersistentCache(temp_cache_dir)

        # テストデータをDataFrameに変換
        test_df = pd.DataFrame(sample_aws_data["EC2"])

        # データを保存
        result = cache.set_cached_data("EC2", "us-east-1", "sandbox", test_df)
        assert isinstance(result, bool)

    def test_clear_cache_operations(self, temp_cache_dir):
        """キャッシュクリア操作のテスト"""
        cache = PersistentCache(temp_cache_dir)

        # 全キャッシュクリア
        cleared_count = cache.clear_cache()
        assert isinstance(cleared_count, int)
        assert cleared_count >= 0

        # 特定サービスのキャッシュクリア
        cleared_count = cache.clear_cache(
            service="EC2", region="us-east-1", profile="sandbox"
        )
        assert isinstance(cleared_count, int)
        assert cleared_count >= 0

    def test_get_cache_info(self, temp_cache_dir):
        """キャッシュ情報取得のテスト"""
        cache = PersistentCache(temp_cache_dir)

        # キャッシュ情報取得
        info = cache.get_cache_info("EC2", "us-east-1", "sandbox")

        assert isinstance(info, dict)
        assert "status" in info

    @pytest.mark.parametrize(
        "service,region,profile",
        [
            ("EC2", "us-east-1", "sandbox"),
            ("RDS", "ap-northeast-1", "production"),
            ("S3", "eu-west-1", None),
            ("Lambda", "us-west-2", "test"),
        ],
    )
    def test_cache_key_generation(
        self, temp_cache_dir, service, region, profile
    ):
        """様々なパラメータでのキャッシュキー生成テスト"""
        cache = PersistentCache(temp_cache_dir)

        key = cache.get_cache_key(service, region, profile)

        assert service in key
        assert region in key

        if profile:
            assert profile in key
        else:
            assert "default" in key


class TestCacheInstance:
    """キャッシュインスタンス取得のテスト"""

    def test_get_cache_instance(self):
        """キャッシュインスタンス取得のテスト"""
        cache = get_cache_instance()
        assert isinstance(cache, PersistentCache)

        # 同じインスタンスが返されることを確認（シングルトン的動作）
        cache2 = get_cache_instance()
        assert cache is cache2


class TestCacheIntegration:
    """キャッシュの統合テスト"""

    def test_cache_workflow_basic(self, temp_cache_dir, sample_aws_data):
        """基本的なキャッシュワークフローのテスト"""
        cache = PersistentCache(temp_cache_dir)

        # 1. 初期状態（キャッシュなし）
        result = cache.get_cached_data("EC2", "us-east-1", "sandbox")
        assert result is None

        # 2. データを保存
        test_df = pd.DataFrame(sample_aws_data["EC2"])
        save_result = cache.set_cached_data(
            "EC2", "us-east-1", "sandbox", test_df
        )
        assert isinstance(save_result, bool)

        # 3. キャッシュをクリア
        cleared_count = cache.clear_cache()
        assert isinstance(cleared_count, int)

    def test_multiple_services_operations(
        self, temp_cache_dir, sample_aws_data
    ):
        """複数サービスの操作テスト"""
        cache = PersistentCache(temp_cache_dir)

        # 複数サービスのデータ操作
        services = ["EC2", "RDS", "S3", "Lambda"]
        for service in services:
            test_df = pd.DataFrame(sample_aws_data[service])
            result = cache.set_cached_data(
                service, "us-east-1", "sandbox", test_df
            )
            assert isinstance(result, bool)

        # キャッシュ情報を確認
        for service in services:
            info = cache.get_cache_info(service, "us-east-1", "sandbox")
            assert isinstance(info, dict)
