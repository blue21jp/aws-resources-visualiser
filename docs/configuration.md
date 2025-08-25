# 設定

## 必要なIAM権限

アプリケーションを実行するには、以下のIAM権限が必要です：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeTags",
                "rds:DescribeDBInstances",
                "rds:ListTagsForResource",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketAcl",
                "s3:GetBucketTagging",
                "lambda:ListFunctions",
                "lambda:ListTags"
            ],
            "Resource": "*"
        }
    ]
}
```

## 必須タグ設定変更

`app/shared/config.py` の `REQUIRED_TAGS` リストを編集：

```python
REQUIRED_TAGS: List[str] = [
   "CostProject",  # デフォルト
]
```

## AWS APIリソース上限設定変更

`app/shared/config.py` の `AWS_API_CONFIG` を編集：

```python
AWS_API_CONFIG: Dict[str, Any] = {
    "max_resources_per_service": 1000,  # 各サービスで取得する最大リソース数
    "pagination_page_size": 100,  # デフォルトページサイズ
    "service_page_sizes": {
        "EC2": 1000,     # EC2の最大ページサイズ
        "RDS": 100,      # RDSの推奨ページサイズ
        "S3": 1000,      # S3の最大ページサイズ
        "Lambda": 50,    # Lambdaの最大ページサイズ（APIハードリミット）
    }
}
```

## サポートサービス追加

新しいAWSサービスを追加したい場合は、以下の情報を含めてAIアシスタントに依頼してください：

### 依頼例

```
ECSサービスを追加したい。以下の情報を取得・表示したい：
- クラスター名
- サービス名
- タスク定義
- 実行中タスク数
- 希望タスク数
- ステータス
- 作成日時
- タグ情報
```

### 必要な情報

サービス追加を依頼する際は、以下を明確にしてください：

1. **追加したいサービス名**
   - 例：ECS、EKS、CloudFormation、API Gateway等

2. **取得・表示したい情報**
   - リソース識別子（名前、ID等）
   - ステータス情報
   - 設定情報
   - 作成日時
   - タグ情報（必須）

3. **特別な要件（あれば）**
   - 特定のフィルタリング
   - 概算コスト計算の考慮事項
   - 表示形式の要望

## プロファイルの追加

新しいAWSプロファイルを追加する場合：

1. **AWS CLI でプロファイルを設定**
   ```bash
   aws configure --profile 新しいプロファイル名
   ```

2. **アプリケーション設定を更新**
   `app/shared/config.py` の `AVAILABLE_PROFILES` に追加：
   ```python
   AVAILABLE_PROFILES: List[str] = [
       "sandbox",
       "新しいプロファイル名",  # 追加
   ]
   ```

3. **デフォルトプロファイルの変更（必要に応じて）**
   ```python
   DEFAULT_PROFILE: str = "新しいプロファイル名"
   ```

## リージョンの追加

新しいAWSリージョンを追加する場合：

1. **アプリケーション設定を更新**
   `app/shared/config.py` の `SUPPORTED_REGIONS` に追加：
   ```python
   SUPPORTED_REGIONS: List[str] = [
       "us-east-1",
       "ap-northeast-1",
       "eu-west-1",  # 追加例
   ]
   ```

2. **デフォルトリージョンの変更（必要に応じて）**
   ```python
   DEFAULT_REGION: str = "eu-west-1"
   ```

## バッチ処理設定

### 並列実行数の調整

```python
# app/shared/config.py
MAX_CONCURRENT_SERVICES: int = 3  # デフォルト: 5
```

### ログ設定の変更

```python
# app/shared/config.py
BATCH_LOG_CONFIG: Dict[str, Any] = {
    "log_dir": "/custom/log/path",
    "log_filename": "custom.log",
    "log_level": "DEBUG",
    # ログローテート設定
    "rotation_type": "time",        # 時間ベースローテート
    "when": "midnight",             # 毎日午前0時
    "interval": 1,                  # 1日間隔
    "backup_count": 7,              # 7日分保持
    "date_suffix": "%Y-%m-%d",      # 日付フォーマット
}
```

## キャッシュ設定

### キャッシュディレクトリとTTL

```python
# app/shared/config.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR: str = str(PROJECT_ROOT / "cache")
```

## UI設定

### ページネーション設定

```python
# app/shared/config.py
PAGINATION_CONFIG: Dict[str, Any] = {
    "default_page_size": 10,
    "page_size_options": [5, 10, 20, 50, 100],
    "show_page_info": True,
    "show_total_count": True,
}
```

### 自動更新間隔設定

```python
# app/shared/config.py
AUTO_REFRESH_INTERVAL: int = 5  # 秒単位
```
