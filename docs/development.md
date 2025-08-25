# 開発

## 開発に必要なソフトウェアのセットアップ

Ubuntu/macOS環境でのインストール手順については、[Ubuntu/macOS開発環境セットアップ](setup-ubuntu.md)を参照してください。

## Amazon Q Developer CLI エージェント

このプロジェクトでは、Amazon Q Developer CLIのプロジェクト専用エージェントを使用してコード修正を行うことができます。

```bash
q chat --agent dev
```

プロジェクトルートで上記コマンドを実行すると、このプロジェクト用に設定されたAIエージェントが起動し、以下の機能を利用できます：

- **コード修正・改善**: 既存コードの品質向上やバグ修正
- **新機能追加**: AWSサービスの追加やUI機能の拡張
- **設定変更**: `app/shared/config.py`の設定項目追加・修正
- **ドキュメント更新**: 機能追加に伴うドキュメントの自動更新
- **テストコード生成**: 新機能に対応するテストケースの作成

エージェントは`.amazonq/AmazonQ.md`に定義された開発標準とコード規約に従って作業を行います。

詳細な使用方法については[Amazon Q Developer CLI エージェント開発ガイド](amazonq-agent.md)を参照してください。

## ログ確認

### ローカル環境

```bash
# 通常実行
just run

# デバッグモード
just run-debug
```

### Docker環境

```bash
# ログ確認
just docker-logs
```

### AWS Fargate環境

```bash
# ECS Execでコンテナ内ログ確認
TASK_ARN=$(aws ecs list-tasks \
  --cluster AwsResourceVisualizer-ecs \
  --service-name AwsResourceVisualizer-ecs \
  --query 'taskArns[0]' \
  --output text \
  --profile sandbox)

aws ecs execute-command \
  --cluster AwsResourceVisualizer-ecs \
  --task $TASK_ARN \
  --container app \
  --interactive \
  --command "tail -f /proc/1/fd/1" \
  --profile sandbox
```

## テスト実行

```bash
just pytest
```

**注意**: テスト実行時に以下のディレクトリにファイルが作成されます：
- `./cache/` - テスト用キャッシュファイル（JSON形式）
- `./logs/` - バッチ処理ログファイル（日付付きローテート、7日分保持）

これらはテスト機能の正常動作に必要なファイルです。

## コード品質チェック・型チェック

```bash
just pylint
```

## コード脆弱性チェック

```bash
just pysecurity-check
```

## 開発環境セットアップ

### 開発フロー

1. **依存関係のインストール**
   ```bash
   just pyinstall
   ```

2. **コード品質チェック**
   ```bash
   just pylint
   ```

3. **テスト実行**
   ```bash
   just pytest
   ```

4. **セキュリティチェック**
   ```bash
   just pysecurity-check
   ```

## Docker開発

### Dockerイメージのビルド

```bash
just docker-build
```

### コンテナの起動・停止

```bash
# コンテナを起動
just docker-run

# ログを確認
just docker-logs

# コンテナを停止
just docker-stop
```

## AWS Fargate開発

### ECRへのデプロイ

```bash
# ECRのデプロイ
RAINCMD=rain_deploy PROFILE=sandbox just ecr

# ECRへイメージ登録
PROFILE=sandbox just ecr-build
PROFILE=sandbox just ecr-push
```

### ECS Fargateへのデプロイ

```bash
# VPC情報の設定
cd rainlib
cp rain_inc_map_vpc_id.yml.template rain_inc_map_vpc_id.yml
vi rain_inc_map_vpc_id.yml

# ECS FARGATEのデプロイ
RAINCMD=rain_deploy PROFILE=sandbox just ecs
```

**重要**: ECS Fargateでは、セキュリティ上の理由により、プレフィックスリストで定義されたIPアドレスからのみアクセス可能です。

**アクセス制限の詳細**:
- ポート8501（Streamlitアプリ）へのアクセスは、`rain_inc_map_vpc_id.yml`の`PrefixListSafePublicId`で指定されたプレフィックスリストに含まれるIPアドレスのみ許可
- 不特定多数からのアクセスは制限されています
- アクセスできない場合は、プレフィックスリストの設定を確認してください

### リソースの削除

```bash
RAINCMD=rain_rm PROFILE=sandbox just ecs
RAINCMD=rain_rm PROFILE=sandbox just ecr
```

**注意**: ECR削除前に、事前にイメージを全削除してください。
