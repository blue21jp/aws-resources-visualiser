# バッチ機能

AWS Resource Visualizerは、Webインターフェースに加えて、コマンドラインからのバッチ処理にも対応しています。

## 概要

バッチ処理機能は以下の特徴を持ちます：

- **非同期並列処理**: 複数のAWSサービスから同時にデータを取得
- **キャッシュ機能**: 取得したデータを自動的にキャッシュして高速化
- **重複実行制御**: 同一プロファイル・リージョンでの重複実行防止
- **詳細ログ**: 実行状況を詳細にログ出力
- **JSON出力**: 結果をJSON形式で出力し、他システムとの連携が容易


## 基本的な使用方法

### 1. 全サービスのデータを取得

```bash
./app_batch.py --region us-east-1 --profile sandbox
```

### 2. 特定のサービスのみ取得

```bash
# EC2とRDSのみ取得
./app_batch.py --services EC2 RDS --region us-east-1 --profile sandbox

# S3のみ取得
./app_batch.py --services S3 --region us-east-1 --profile sandbox
```

### 3. キャッシュをクリアして実行

```bash
./app_batch.py --clear-cache --region us-east-1 --profile sandbox
```

### 4. 強制実行（重複実行制御を無視）

```bash
./app_batch.py --force --region us-east-1 --profile sandbox
```

## コマンドライン引数

**`--services`**
- 取得するサービスを指定
- デフォルト: 全サービス
- 例: `--services EC2 RDS`

**`--region`**
- AWSリージョンを指定
- デフォルト: 環境変数から取得
- 例: `--region us-east-1`

**`--profile`**
- AWSプロファイルを指定
- デフォルト: なし
- 例: `--profile sandbox`

**`--clear-cache`**
- キャッシュをクリアして実行
- デフォルト: False
- 例: `--clear-cache`

**`--force`**
- 重複実行制御を無視して強制実行
- デフォルト: False
- 例: `--force`

### サポートサービス

- `EC2`: Amazon Elastic Compute Cloud
- `RDS`: Amazon Relational Database Service
- `S3`: Amazon Simple Storage Service
- `Lambda`: AWS Lambda

## 実行環境別の設定

### Poetry環境（ローカル開発）

```bash
poetry run ./app_batch.py --region us-east-1 --profile sandbox
```

### Docker環境

```bash
docker run -e BATCH_RUN_TYPE=docker \
  -v ~/.aws:/home/appuser/.aws \
  aws-resource-visualizer:latest \
  ./app_batch.py --region us-east-1
```

### ECS Fargate環境

```bash
# IAMロールによる認証、リージョンは環境変数AWS_DEFAULT_REGIONから取得
./app_batch.py
```

### ECS Exec を使用した手動実行

```bash
# 実行中のタスクARNを取得
TASK_ARN=$(aws ecs list-tasks \
  --cluster AwsResourceVisualizer-ecs \
  --service-name AwsResourceVisualizer-ecs \
  --query 'taskArns[0]' \
  --output text \
  --profile sandbox)

# ECS Execでコンテナに接続してバッチ処理を実行
aws ecs execute-command \
  --cluster AwsResourceVisualizer-ecs \
  --task $TASK_ARN \
  --container app \
  --interactive \
  --command "./app_batch.py --region us-east-1" \
  --profile sandbox
```

## 出力形式

### 成功時の出力

```json
{
  "success": true,
  "services": ["EC2", "RDS", "S3", "Lambda"],
  "region": "us-east-1",
  "success_count": 3,
  "total_count": 4,
  "results": {
    "EC2": 5,
    "RDS": 2,
    "S3": 10,
    "Lambda": 0
  }
}
```

### エラー時の出力

```json
{
  "success": false,
  "error": "AWS認証情報が設定されていません",
  "services": ["EC2", "RDS"],
  "region": "us-east-1"
}
```

## ログ出力

### ログファイルの場所とローテート

- **デフォルト**: `{プロジェクトルート}/logs/batch_execution.log`
- **カスタム**: 環境変数`AWS_RESOURCE_VISUALIZER_LOG_DIR`で変更可能

### ログローテート機能

- **ローテート間隔**: 毎日午前0時に自動ローテート
- **ファイル命名**: 日付付きファイル名（例：`batch_execution.log.2025-08-20`）
- **保持期間**: 7日分のログファイルを保持
- **自動削除**: 8日目以降のログファイルは自動削除
- **同日内動作**: 複数回実行時は同一ファイルに追記

**生成されるファイル例：**
```
logs/
├── batch_execution.log          # 現在のログファイル
├── batch_execution.log.2025-08-19  # 1日前
├── batch_execution.log.2025-08-18  # 2日前
├── batch_execution.log.2025-08-17  # 3日前
├── batch_execution.log.2025-08-16  # 4日前
├── batch_execution.log.2025-08-15  # 5日前
├── batch_execution.log.2025-08-14  # 6日前
└── batch_execution.log.2025-08-13  # 7日前
```

### ログレベル

- **INFO**: 実行状況、取得結果
- **WARNING**: データ取得失敗、キャッシュ関連の警告
- **ERROR**: 認証エラー、API呼び出しエラー
- **DEBUG**: 詳細なデバッグ情報

## 設定のカスタマイズ

### 並列実行数の調整

`app/shared/config.py`の`MAX_CONCURRENT_SERVICES`を変更：

```python
# 同時実行するサービス数の上限（デフォルト: 5）
MAX_CONCURRENT_SERVICES: int = 3
```

### ログ設定の変更

`app/shared/config.py`の`BATCH_LOG_CONFIG`を変更：

```python
BATCH_LOG_CONFIG: Dict[str, Any] = {
    "log_dir": "/custom/log/path",  # ログディレクトリ
    "log_filename": "custom.log",   # ログファイル名
    "log_level": "DEBUG",           # ログレベル
    # ログローテート設定
    "rotation_type": "time",        # 時間ベースローテート
    "when": "midnight",             # 毎日午前0時
    "interval": 1,                  # 1日間隔
    "backup_count": 7,              # 7日分保持
    "date_suffix": "%Y-%m-%d",      # 日付フォーマット
}
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 認証エラー

**エラー**: `AWS認証情報が設定されていません`

**解決方法**:
- AWS CLI設定を確認: `aws configure list --profile sandbox`
- IAM権限を確認（[設定ドキュメント](configuration.md)参照）

#### 2. 重複実行エラー

**エラー**: `同じ条件でバッチが実行中です。--forceオプションで強制実行できます。`

**原因**: 同じプロファイル・リージョンの組み合わせで既に実行中

**解決方法**:
- `--force`オプションで強制実行
- 異なるプロファイルまたはリージョンで実行

#### 3. メモリ不足

**解決方法**:
- 並列実行数を減らす: `MAX_CONCURRENT_SERVICES`を調整
- 特定のサービスのみ実行: `--services EC2`

## パフォーマンス最適化

### 推奨設定

- **小規模環境**（リソース数 < 100）: `MAX_CONCURRENT_SERVICES = 5`
- **中規模環境**（リソース数 100-1000）: `MAX_CONCURRENT_SERVICES = 3`
- **大規模環境**（リソース数 > 1000）: `MAX_CONCURRENT_SERVICES = 2`

### キャッシュ活用

- 初回実行後はキャッシュが有効（24時間）
- 頻繁な実行時は`--clear-cache`を避ける

## セキュリティ考慮事項

### 認証情報の管理

- **本番環境**: IAMロールを使用（推奨）
- **開発環境**: プロファイル設定を使用
- **CI/CD**: 環境変数またはシークレット管理サービスを使用

### ログの取り扱い

- ログファイルに認証情報が含まれないことを確認
- ログファイルのアクセス権限を適切に設定
