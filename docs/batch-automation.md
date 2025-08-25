# バッチ自動化

バッチ処理は、GitHub ActionsとECS Execを組み合わせた自動化に対応しています。

## 自動化構成

### GitHub Actions
- **バッチ実行**: ECS Exec経由でのリモートバッチ処理実行
- **スケジュール実行**: 定期的な自動実行

### ECS Exec
- **リモート実行**: 実行中のECS Fargateタスク内でバッチ処理を実行
- **セッション管理**: AWS Session Manager Plugin経由での安全な接続

## GitHub Actions ワークフロー

### バッチ実行ワークフロー (`run_batch.yml`)

**トリガー**:
- 手動実行（`workflow_dispatch`）
- スケジュール実行（毎日午前2時UTC）

**必要なシークレット**:
- `AWS_IAM_ROLE_BATCH`: バッチ実行用IAMロールARN

**実行内容**:

**1. 環境セットアップ**
- Session Manager Pluginインストール

**2. AWS認証**
- OIDC認証によるIAMロール引き受け

**3. ECSタスク検索**
- 実行中のECS Fargateタスクを自動検出
- タスクが見つからない場合はエラー終了

**4. バッチ実行**
- ECS Exec経由でバッチ処理を実行
- キャッシュクリア付きで実行

## IAMロール設定

### バッチ実行用ロール (`GithubActionsRoleBatch`)

**信頼関係**:
- GitHub Actions OIDC Provider
- act（ローカルテスト）用のAssumeRole

**権限**:
- ECS操作（タスク一覧・実行・説明）
- アカウント情報取得

## justfile タスク

### バッチ自動化関連タスク

**GitHub Actions**:
- `act-batch`: バッチワークフローのローカル実行
- `gha-install`: ワークフローファイルの配置

**AWS デプロイ**:
- `gha-role`: GitHub Actions用IAMロール作成

## デプロイフロー

### 初回セットアップ

1. **IAMロール作成**
   - GitHub Actions用のバッチ実行ロールを作成

2. **ECS Fargateサービス起動**
   - バッチ処理を実行するECSサービスが稼働中である必要

3. **GitHub Secretsの設定**
   - バッチ実行用IAMロールARNを設定

### 自動実行の有効化

**スケジュール実行を有効にする場合**:
- `gha/run_batch.yml`のschedule設定のコメントアウトを解除
- 毎日午前2時（UTC）に自動実行される設定
- **注意**: デフォルトではスケジュール実行は無効化されており、手動実行のみ可能

## 実行方式

### ECS Exec方式の特徴

**利点**:
- 既存のECS Fargateインフラを活用
- サーバーレスでの定期実行
- AWS認証情報の安全な管理

**制約**:
- ECS Fargateタスクが実行中である必要
- Session Manager Pluginが必要
- ECS Execが有効化されたタスク定義が必要

## ローカルテスト

### act を使用したテスト

バッチワークフローをローカルでテストできます（要AWS認証）。
```bash
PROFILE=sandbox ACT_PROFILE=sandbox just act-batch
```
