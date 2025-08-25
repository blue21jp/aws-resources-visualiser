#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWSクライアントのテスト"""

# Standard Library
from datetime import datetime
from unittest.mock import patch

# Third Party Library
import pandas as pd
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# First Party Library
from app.shared.aws_client import (
    _format_datetime,
    _handle_aws_exceptions,
    get_ec2_instances,
    get_lambda_functions,
    get_rds_instances,
    get_s3_buckets,
)


class TestUtilityFunctions:
    """ユーティリティ関数のテストクラス"""

    def test_format_datetime_with_datetime(self):
        """日時オブジェクトのフォーマットテスト"""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = _format_datetime(dt)
        assert result == "2024-01-01 12:30:45"

    def test_format_datetime_with_none(self):
        """None値の日時フォーマットテスト"""
        result = _format_datetime(None)
        assert result == ""

    def test_format_datetime_with_default(self):
        """デフォルト値指定の日時フォーマットテスト"""
        result = _format_datetime(None, "N/A")
        assert result == "N/A"

    def test_handle_aws_exceptions_decorator(self):
        """AWS例外処理デコレータのテスト"""

        @_handle_aws_exceptions("TestService")
        def test_function():
            raise NoCredentialsError()

        with pytest.raises(Exception) as exc_info:
            test_function()

        assert "AWS認証情報が設定されていません" in str(exc_info.value)

    def test_handle_aws_exceptions_client_error(self):
        """ClientError例外処理のテスト"""

        @_handle_aws_exceptions("TestService")
        def test_function():
            error_response = {
                "Error": {"Code": "AccessDenied", "Message": "Access denied"}
            }
            raise ClientError(error_response, "TestOperation")

        with pytest.raises(Exception) as exc_info:
            test_function()

        assert "TestServiceデータ取得エラー (AccessDenied)" in str(
            exc_info.value
        )

    def test_handle_aws_exceptions_generic_error(self):
        """一般的な例外処理のテスト"""

        @_handle_aws_exceptions("TestService")
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(Exception) as exc_info:
            test_function()

        assert "TestServiceデータ取得で予期しないエラー" in str(exc_info.value)


class TestEC2Resources:
    """EC2リソース取得のテストクラス"""

    def test_get_ec2_resources_success(self, aws_mock, sample_ec2_instances):
        """EC2リソース取得成功のテスト"""
        result = get_ec2_instances("us-east-1")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

        # 必要なカラムが存在することを確認
        expected_columns = [
            "Instance ID",
            "Name",
            "State",
            "Instance Type",
            "Availability Zone",
            "Public IP",
            "Private IP",
            "Launch Time",
            "Required Tags",
            "Tags Dict",
        ]
        for col in expected_columns:
            assert col in result.columns

        # タグ付きインスタンスの確認
        tagged_instance = result[result["Name"] == "test-instance-1"]
        if len(tagged_instance) > 0:
            tagged_instance = tagged_instance.iloc[0]
            assert "CostProject" in str(tagged_instance.get("Tags Dict", {}))

        # タグなしインスタンスの確認
        untagged_instance = result[result["Name"] == "test-instance-2"]
        if len(untagged_instance) > 0:
            untagged_instance = untagged_instance.iloc[0]
            # タグなしでも正常に処理されることを確認
            assert isinstance(
                untagged_instance.get("Tags Dict", {}), (dict, str)
            )

    def test_get_ec2_resources_no_instances(self, aws_mock):
        """インスタンスが存在しない場合のテスト"""
        result = get_ec2_instances("us-west-2")  # 別リージョン

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch("app.shared.aws_client.boto3.Session")
    def test_get_ec2_resources_credentials_error(self, mock_session):
        """認証エラーのテスト"""
        mock_session.return_value.client.side_effect = NoCredentialsError()

        with pytest.raises(Exception) as exc_info:
            get_ec2_instances("us-east-1")

        assert "AWS認証情報が設定されていません" in str(exc_info.value)


class TestRDSResources:
    """RDSリソース取得のテストクラス"""

    def test_get_rds_resources_success(self, aws_mock, sample_rds_instances):
        """RDSリソース取得成功のテスト"""
        result = get_rds_instances("us-east-1")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

        # 必要なカラムが存在することを確認
        expected_columns = [
            "DB Identifier",
            "Engine",
            "DB Instance Class",
            "Status",
            "Availability Zone",
            "Multi-AZ",
            "Storage Type",
            "Allocated Storage",
            "Created Time",
            "Required Tags",
            "Tags Dict",
        ]
        for col in expected_columns:
            assert col in result.columns

        # タグ付きインスタンスの確認
        tagged_instance = result[
            result["DB Identifier"].str.contains("test-db-1", na=False)
        ]
        if len(tagged_instance) > 0:
            tagged_instance = tagged_instance.iloc[0]
            assert "CostProject" in str(tagged_instance.get("Tags Dict", {}))

    def test_get_rds_resources_no_instances(self, aws_mock):
        """RDSインスタンスが存在しない場合のテスト"""
        result = get_rds_instances("us-west-2")  # 別リージョン

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestS3Resources:
    """S3リソース取得のテストクラス"""

    def test_get_s3_resources_success(self, aws_mock, sample_s3_buckets):
        """S3リソース取得成功のテスト"""
        result = get_s3_buckets()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

        # 必要なカラムが存在することを確認
        expected_columns = [
            "Bucket Name",
            "Region",
            "Created Date",
            "Public Access",
            "Required Tags",
            "Tags Dict",
        ]
        for col in expected_columns:
            assert col in result.columns

        # タグ付きバケットの確認
        tagged_bucket = result[
            result["Bucket Name"].str.contains("test-bucket-1", na=False)
        ]
        if len(tagged_bucket) > 0:
            tagged_bucket = tagged_bucket.iloc[0]
            assert "CostProject" in str(tagged_bucket.get("Tags Dict", {}))

    def test_get_s3_resources_no_buckets(self, aws_mock):
        """S3バケットが存在しない場合のテスト"""
        result = get_s3_buckets()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestLambdaResources:
    """Lambdaリソース取得のテストクラス"""

    def test_get_lambda_resources_success(
        self, aws_mock, sample_lambda_functions
    ):
        """Lambdaリソース取得成功のテスト"""
        result = get_lambda_functions("us-east-1")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

        # 必要なカラムが存在することを確認
        expected_columns = [
            "Function Name",
            "Runtime",
            "Handler",
            "Code Size",
            "Memory",
            "Timeout",
            "Last Modified",
            "State",
            "Role",
            "Required Tags",
            "Tags Dict",
        ]
        for col in expected_columns:
            assert col in result.columns

        # タグ付き関数の確認
        tagged_function = result[
            result["Function Name"].str.contains("test-function-1", na=False)
        ]
        if len(tagged_function) > 0:
            tagged_function = tagged_function.iloc[0]
            assert "CostProject" in str(tagged_function.get("Tags Dict", {}))

    def test_get_lambda_resources_no_functions(self, aws_mock):
        """Lambda関数が存在しない場合のテスト"""
        result = get_lambda_functions("us-west-2")  # 別リージョン

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestResourceIntegration:
    """リソース取得の統合テスト"""

    def test_all_services_data_consistency(
        self,
        aws_mock,
        sample_ec2_instances,
        sample_rds_instances,
        sample_s3_buckets,
        sample_lambda_functions,
    ):
        """全サービスのデータ整合性テスト"""
        services = {
            "EC2": get_ec2_instances,
            "RDS": get_rds_instances,
            "S3": get_s3_buckets,
            "Lambda": get_lambda_functions,
        }

        results = {}
        for service_name, get_function in services.items():
            if service_name == "S3":
                results[service_name] = get_function()  # S3は引数なし
            else:
                results[service_name] = get_function("us-east-1")

        # 全サービスでDataFrameが返されることを確認
        for service_name, df in results.items():
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2  # 各サービス2つのリソース

            # 共通カラムの存在確認
            assert "Tags Dict" in df.columns or "Required Tags" in df.columns

            # データが取得されていることを確認
            if len(df) > 0:
                # 各行にデータが含まれていることを確認
                assert not df.empty

    @pytest.mark.parametrize(
        "service_function,region",
        [
            (get_ec2_instances, "us-east-1"),
            (get_rds_instances, "us-east-1"),
            (get_s3_buckets, None),  # S3はリージョン不要
            (get_lambda_functions, "us-east-1"),
        ],
    )
    def test_service_functions_with_different_regions(
        self, aws_mock, service_function, region
    ):
        """異なるリージョンでのサービス関数テスト"""
        if region:
            result = service_function(region)
        else:
            result = service_function()
        assert isinstance(result, pd.DataFrame)

    def test_tag_processing_consistency(
        self,
        aws_mock,
        sample_ec2_instances,
        sample_rds_instances,
        sample_s3_buckets,
        sample_lambda_functions,
    ):
        """タグ処理の一貫性テスト"""
        services = [
            get_ec2_instances,
            get_rds_instances,
            get_s3_buckets,
            get_lambda_functions,
        ]

        for service_function in services:
            if service_function == get_s3_buckets:
                result = service_function()
            else:
                result = service_function("us-east-1")

            # データが取得されていることを確認
            assert isinstance(result, pd.DataFrame)

            # タグ関連カラムの存在確認
            has_tags_dict = "Tags Dict" in result.columns
            has_required_tags = "Required Tags" in result.columns

            assert has_tags_dict or has_required_tags

            # データが存在する場合のタグ形式確認
            if len(result) > 0 and has_tags_dict:
                for _, row in result.iterrows():
                    tags_value = row.get("Tags Dict", {})
                    # タグは辞書形式または文字列形式
                    assert isinstance(tags_value, (dict, str, type(None)))
