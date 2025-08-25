#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テスト共通設定とフィクスチャ"""

# Standard Library
import os
import tempfile
from typing import Any, Dict, Generator
from unittest.mock import patch

# Third Party Library
import boto3
import pytest
from moto import mock_aws


@pytest.fixture(scope="session", autouse=True)
def aws_credentials() -> Generator[None, None, None]:
    """AWS認証情報をダミー値に設定（実環境へのアクセスを防止）"""
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    ):
        yield


@pytest.fixture
def aws_mock():
    """最新moto仕様でのAWSサービスモック"""
    with mock_aws():
        yield


@pytest.fixture
def ec2_client(aws_mock):
    """モック化されたEC2クライアント"""
    return boto3.client("ec2", region_name="us-east-1")


@pytest.fixture
def rds_client(aws_mock):
    """モック化されたRDSクライアント"""
    return boto3.client("rds", region_name="us-east-1")


@pytest.fixture
def s3_client(aws_mock):
    """モック化されたS3クライアント"""
    return boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def lambda_client(aws_mock):
    """モック化されたLambdaクライアント"""
    return boto3.client("lambda", region_name="us-east-1")


@pytest.fixture
def iam_client(aws_mock):
    """モック化されたIAMクライアント"""
    return boto3.client("iam", region_name="us-east-1")


@pytest.fixture
def sample_ec2_instances(ec2_client):
    """テスト用EC2インスタンスを作成"""
    # VPCとサブネットを作成
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
    subnet_id = subnet["Subnet"]["SubnetId"]

    # インスタンスを作成
    instances = []

    # タグ付きインスタンス
    response1 = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro",
        SubnetId=subnet_id,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": "test-instance-1"},
                    {"Key": "CostProject", "Value": "project-a"},
                ],
            }
        ],
    )
    instances.append(response1["Instances"][0]["InstanceId"])

    # タグなしインスタンス
    response2 = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.small",
        SubnetId=subnet_id,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": "test-instance-2"}],
            }
        ],
    )
    instances.append(response2["Instances"][0]["InstanceId"])

    return instances


@pytest.fixture
def sample_rds_instances(rds_client):
    """テスト用RDSインスタンスを作成"""
    instances = []

    # タグ付きRDSインスタンス
    rds_client.create_db_instance(
        DBInstanceIdentifier="test-db-1",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
        Tags=[
            {"Key": "Name", "Value": "test-db-1"},
            {"Key": "CostProject", "Value": "project-a"},
        ],
    )
    instances.append("test-db-1")

    # タグなしRDSインスタンス
    rds_client.create_db_instance(
        DBInstanceIdentifier="test-db-2",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
        Tags=[{"Key": "Name", "Value": "test-db-2"}],
    )
    instances.append("test-db-2")

    return instances


@pytest.fixture
def sample_s3_buckets(s3_client):
    """テスト用S3バケットを作成"""
    buckets = []

    # タグ付きバケット
    bucket_name_1 = "test-bucket-1"
    s3_client.create_bucket(Bucket=bucket_name_1)
    s3_client.put_bucket_tagging(
        Bucket=bucket_name_1,
        Tagging={
            "TagSet": [
                {"Key": "Name", "Value": "test-bucket-1"},
                {"Key": "CostProject", "Value": "project-a"},
            ]
        },
    )
    buckets.append(bucket_name_1)

    # タグなしバケット
    bucket_name_2 = "test-bucket-2"
    s3_client.create_bucket(Bucket=bucket_name_2)
    s3_client.put_bucket_tagging(
        Bucket=bucket_name_2,
        Tagging={"TagSet": [{"Key": "Name", "Value": "test-bucket-2"}]},
    )
    buckets.append(bucket_name_2)

    return buckets


@pytest.fixture
def sample_lambda_functions(lambda_client, iam_client):
    """テスト用Lambda関数を作成"""
    # Standard Library
    import json

    # Lambda実行ロールを作成
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    iam_client.create_role(
        RoleName="lambda-role",
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Path="/",
    )

    role_arn = "arn:aws:iam::123456789012:role/lambda-role"
    functions = []

    # タグ付きLambda関数
    function_name_1 = "test-function-1"
    lambda_client.create_function(
        FunctionName=function_name_1,
        Runtime="python3.9",
        Role=role_arn,
        Handler="index.handler",
        Code={"ZipFile": b"fake code"},
        Tags={
            "Name": "test-function-1",
            "CostProject": "project-a",
        },
    )
    functions.append(function_name_1)

    # タグなしLambda関数
    function_name_2 = "test-function-2"
    lambda_client.create_function(
        FunctionName=function_name_2,
        Runtime="python3.9",
        Role=role_arn,
        Handler="index.handler",
        Code={"ZipFile": b"fake code"},
        Tags={"Name": "test-function-2"},
    )
    functions.append(function_name_2)

    return functions


@pytest.fixture
def temp_cache_dir():
    """テスト用の一時キャッシュディレクトリ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("app.shared.config.CACHE_DIR", temp_dir):
            yield temp_dir


@pytest.fixture
def mock_streamlit_session():
    """Streamlitセッション状態のモック"""
    session_state: Dict[str, Any] = {}

    class MockSessionState:
        def __getattr__(self, key):
            return session_state.get(key)

        def __setattr__(self, key, value):
            session_state[key] = value

        def __contains__(self, key):
            return key in session_state

        def get(self, key, default=None):
            return session_state.get(key, default)

    return MockSessionState()


@pytest.fixture
def sample_aws_data():
    """テスト用のAWSデータサンプル"""
    return {
        "EC2": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "Name": "test-instance-1",
                "State": "running",
                "InstanceType": "t3.micro",
                "AvailabilityZone": "us-east-1a",
                "PublicIpAddress": "1.2.3.4",
                "PrivateIpAddress": "10.0.1.10",
                "LaunchTime": "2024-01-01T00:00:00Z",
                "Tags": {"CostProject": "project-a"},
                "HasRequiredTags": True,
            },
            {
                "InstanceId": "i-0987654321fedcba0",
                "Name": "test-instance-2",
                "State": "running",
                "InstanceType": "t3.small",
                "AvailabilityZone": "us-east-1b",
                "PublicIpAddress": None,
                "PrivateIpAddress": "10.0.1.11",
                "LaunchTime": "2024-01-02T00:00:00Z",
                "Tags": {},
                "HasRequiredTags": False,
            },
        ],
        "RDS": [
            {
                "DBInstanceIdentifier": "test-db-1",
                "Engine": "mysql",
                "DBInstanceClass": "db.t3.micro",
                "DBInstanceStatus": "available",
                "AvailabilityZone": "us-east-1a",
                "MultiAZ": False,
                "StorageType": "gp2",
                "AllocatedStorage": 20,
                "InstanceCreateTime": "2024-01-01T00:00:00Z",
                "Tags": {"CostProject": "project-a"},
                "HasRequiredTags": True,
            },
            {
                "DBInstanceIdentifier": "test-db-2",
                "Engine": "postgres",
                "DBInstanceClass": "db.t3.micro",
                "DBInstanceStatus": "available",
                "AvailabilityZone": "us-east-1b",
                "MultiAZ": False,
                "StorageType": "gp2",
                "AllocatedStorage": 20,
                "InstanceCreateTime": "2024-01-02T00:00:00Z",
                "Tags": {},
                "HasRequiredTags": False,
            },
        ],
        "S3": [
            {
                "Name": "test-bucket-1",
                "Region": "us-east-1",
                "CreationDate": "2024-01-01T00:00:00Z",
                "PublicAccessBlock": True,
                "Tags": {"CostProject": "project-a"},
                "HasRequiredTags": True,
            },
            {
                "Name": "test-bucket-2",
                "Region": "us-east-1",
                "CreationDate": "2024-01-02T00:00:00Z",
                "PublicAccessBlock": True,
                "Tags": {},
                "HasRequiredTags": False,
            },
        ],
        "Lambda": [
            {
                "FunctionName": "test-function-1",
                "Runtime": "python3.9",
                "Handler": "index.handler",
                "CodeSize": 1024,
                "MemorySize": 128,
                "Timeout": 30,
                "LastModified": "2024-01-01T00:00:00Z",
                "State": "Active",
                "Role": "arn:aws:iam::123456789012:role/lambda-role",
                "Tags": {"CostProject": "project-a"},
                "HasRequiredTags": True,
            },
            {
                "FunctionName": "test-function-2",
                "Runtime": "python3.9",
                "Handler": "index.handler",
                "CodeSize": 2048,
                "MemorySize": 256,
                "Timeout": 60,
                "LastModified": "2024-01-02T00:00:00Z",
                "State": "Active",
                "Role": "arn:aws:iam::123456789012:role/lambda-role",
                "Tags": {},
                "HasRequiredTags": False,
            },
        ],
    }
