#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - AWSクライアント"""

# Standard Library
from datetime import datetime
from typing import Dict, Optional, Union

# Third Party Library
import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError

# Local Library
from .config import AWS_API_CONFIG, REQUIRED_TAGS


def _format_datetime(dt_obj: Union[datetime, None], default: str = "") -> str:
    """日時オブジェクトを文字列にフォーマット"""
    if dt_obj:
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    return default


def _handle_aws_exceptions(service_name: str):
    """AWS例外を統一的に処理するデコレータ"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except NoCredentialsError:
                raise Exception(
                    "AWS認証情報が設定されていません。~/.aws/credentials または環境変数を確認してください。"
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get(
                    "Message", str(e)
                )
                raise Exception(
                    f"{service_name}データ取得エラー ({error_code}): {error_message}"
                )
            except Exception as e:
                raise Exception(
                    f"{service_name}データ取得で予期しないエラー: {str(e)}"
                )

        return wrapper

    return decorator


def get_boto3_session(profile_name: Optional[str] = None) -> boto3.Session:
    """指定されたプロファイルでBoto3セッションを作成"""
    # Local Library
    from .config import get_effective_profile

    # 実行環境に応じた有効なプロファイルを取得
    effective_profile = get_effective_profile(profile_name)

    if effective_profile:
        return boto3.Session(profile_name=effective_profile)
    else:
        return boto3.Session()


def format_required_tags(tags_dict: Dict[str, str]) -> str:
    """必須タグのみを抽出してフォーマット"""
    required_tags_only = {}
    for tag_key in REQUIRED_TAGS:
        if tag_key in tags_dict:
            required_tags_only[tag_key] = tags_dict[tag_key]

    if required_tags_only:
        return ", ".join([f"{k}:{v}" for k, v in required_tags_only.items()])
    return ""


@_handle_aws_exceptions("EC2")
def get_ec2_instances(
    region: str, profile_name: Optional[str] = None
) -> pd.DataFrame:
    """EC2インスタンス情報を取得（ページネーション対応、terminated状態を除外）"""
    session = get_boto3_session(profile_name)
    ec2 = session.client("ec2", region_name=region)

    instances = []
    total_count = 0
    max_resources = AWS_API_CONFIG["max_resources_per_service"]
    page_size = AWS_API_CONFIG["service_page_sizes"].get(
        "EC2", AWS_API_CONFIG["pagination_page_size"]
    )

    # terminated状態のインスタンスを除外するフィルターを追加
    paginator = ec2.get_paginator("describe_instances")
    page_iterator = paginator.paginate(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running",
                    "shutting-down",
                    "stopping",
                    "stopped",
                ],
            }
        ],
        PaginationConfig={
            "PageSize": page_size,
            "MaxItems": max_resources,
        },
    )

    for page in page_iterator:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                if total_count >= max_resources:
                    break

                name = ""
                tags_str = ""
                tags_dict = {}
                if "Tags" in instance:
                    tags_dict = {
                        tag["Key"]: tag["Value"] for tag in instance["Tags"]
                    }
                    name = tags_dict.get("Name", "")
                    tags_str = format_required_tags(tags_dict)

                instances.append(
                    {
                        "Instance ID": instance["InstanceId"],
                        "Name": name,
                        "State": instance["State"]["Name"],
                        "Instance Type": instance["InstanceType"],
                        "Availability Zone": instance["Placement"][
                            "AvailabilityZone"
                        ],
                        "Public IP": instance.get("PublicIpAddress", ""),
                        "Private IP": instance.get("PrivateIpAddress", ""),
                        "Launch Time": _format_datetime(
                            instance.get("LaunchTime")
                        ),
                        "Required Tags": tags_str,
                        "Tags Dict": tags_dict,
                    }
                )
                total_count += 1

            if total_count >= max_resources:
                break
        if total_count >= max_resources:
            break

    return pd.DataFrame(instances)


@_handle_aws_exceptions("RDS")
def get_rds_instances(
    region: str, profile_name: Optional[str] = None
) -> pd.DataFrame:
    """RDSインスタンス情報を取得（ページネーション対応）"""
    session = get_boto3_session(profile_name)
    rds = session.client("rds", region_name=region)

    instances = []
    total_count = 0
    max_resources = AWS_API_CONFIG["max_resources_per_service"]
    page_size = AWS_API_CONFIG["service_page_sizes"].get(
        "RDS", AWS_API_CONFIG["pagination_page_size"]
    )

    paginator = rds.get_paginator("describe_db_instances")
    page_iterator = paginator.paginate(
        PaginationConfig={
            "PageSize": page_size,
            "MaxItems": max_resources,
        }
    )

    for page in page_iterator:
        for db in page["DBInstances"]:
            if total_count >= max_resources:
                break

            tags_str = ""
            tags_dict = {}
            try:
                tags_response = rds.list_tags_for_resource(
                    ResourceName=db["DBInstanceArn"]
                )
                if tags_response["TagList"]:
                    tags_dict = {
                        tag["Key"]: tag["Value"]
                        for tag in tags_response["TagList"]
                    }
                    tags_str = format_required_tags(tags_dict)
            except ClientError:
                pass

            instances.append(
                {
                    "DB Identifier": db["DBInstanceIdentifier"],
                    "Engine": f"{db['Engine']} {db.get('EngineVersion', '')}",
                    "DB Instance Class": db["DBInstanceClass"],
                    "Status": db["DBInstanceStatus"],
                    "Availability Zone": db.get("AvailabilityZone", ""),
                    "Multi-AZ": db.get("MultiAZ", False),
                    "Storage Type": db.get("StorageType", ""),
                    "Allocated Storage": f"{db.get('AllocatedStorage', 0)} GB",
                    "Created Time": _format_datetime(
                        db.get("InstanceCreateTime")
                    ),
                    "Required Tags": tags_str,
                    "Tags Dict": tags_dict,
                }
            )
            total_count += 1
        if total_count >= max_resources:
            break

    return pd.DataFrame(instances)


@_handle_aws_exceptions("S3")
def get_s3_buckets(profile_name: Optional[str] = None) -> pd.DataFrame:
    """S3バケット情報を取得（ページネーション対応）"""
    session = get_boto3_session(profile_name)
    s3 = session.client("s3")

    buckets = []
    total_count = 0
    max_resources = AWS_API_CONFIG["max_resources_per_service"]
    page_size = AWS_API_CONFIG["service_page_sizes"].get(
        "S3", AWS_API_CONFIG["pagination_page_size"]
    )

    paginator = s3.get_paginator("list_buckets")
    page_iterator = paginator.paginate(
        PaginationConfig={
            "PageSize": page_size,
            "MaxItems": max_resources,
        }
    )

    for page in page_iterator:
        for bucket in page["Buckets"]:
            if total_count >= max_resources:
                break

            bucket_name = bucket["Name"]

            try:
                location_response = s3.get_bucket_location(Bucket=bucket_name)
                region = location_response["LocationConstraint"] or "us-east-1"
            except ClientError:
                region = "Unknown"

            public_access = "Unknown"
            try:
                acl_response = s3.get_bucket_acl(Bucket=bucket_name)
                public_access = "Private"
                for grant in acl_response.get("Grants", []):
                    grantee = grant.get("Grantee", {})
                    if grantee.get(
                        "Type"
                    ) == "Group" and "AllUsers" in grantee.get("URI", ""):
                        public_access = "Public"
                        break
            except ClientError:
                pass

            tags_str = ""
            tags_dict = {}
            try:
                tags_response = s3.get_bucket_tagging(Bucket=bucket_name)
                if tags_response.get("TagSet"):
                    tags_dict = {
                        tag["Key"]: tag["Value"]
                        for tag in tags_response["TagSet"]
                    }
                    tags_str = format_required_tags(tags_dict)
            except ClientError:
                pass

            buckets.append(
                {
                    "Bucket Name": bucket_name,
                    "Region": region,
                    "Created Date": _format_datetime(bucket["CreationDate"]),
                    "Public Access": public_access,
                    "Required Tags": tags_str,
                    "Tags Dict": tags_dict,
                }
            )
            total_count += 1
        if total_count >= max_resources:
            break

    return pd.DataFrame(buckets)


@_handle_aws_exceptions("Lambda")
def get_lambda_functions(
    region: str, profile_name: Optional[str] = None
) -> pd.DataFrame:
    """Lambda関数情報を取得（ページネーション対応）"""
    session = get_boto3_session(profile_name)
    lambda_client = session.client("lambda", region_name=region)

    functions = []
    total_count = 0
    max_resources = AWS_API_CONFIG["max_resources_per_service"]
    page_size = AWS_API_CONFIG["service_page_sizes"].get(
        "Lambda", AWS_API_CONFIG["pagination_page_size"]
    )

    paginator = lambda_client.get_paginator("list_functions")
    page_iterator = paginator.paginate(
        PaginationConfig={
            "PageSize": page_size,
            "MaxItems": max_resources,
        }
    )

    for page in page_iterator:
        for func in page["Functions"]:
            if total_count >= max_resources:
                break

            tags_str = ""
            tags_dict = {}
            try:
                tags_response = lambda_client.list_tags(
                    Resource=func["FunctionArn"]
                )
                if tags_response.get("Tags"):
                    tags_dict = tags_response["Tags"]
                    tags_str = format_required_tags(tags_dict)
            except ClientError:
                pass

            functions.append(
                {
                    "Function Name": func["FunctionName"],
                    "Runtime": func.get("Runtime", ""),
                    "Handler": func.get("Handler", ""),
                    "Code Size": f"{func.get('CodeSize', 0) / 1024 / 1024:.2f} MB",
                    "Memory": f"{func.get('MemorySize', 0)} MB",
                    "Timeout": f"{func.get('Timeout', 0)} seconds",
                    "Last Modified": func.get("LastModified", ""),
                    "State": func.get("State", ""),
                    "Role": (
                        func.get("Role", "").split("/")[-1]
                        if func.get("Role")
                        else ""
                    ),
                    "Required Tags": tags_str,
                    "Tags Dict": tags_dict,
                }
            )
            total_count += 1
        if total_count >= max_resources:
            break

    return pd.DataFrame(functions)
