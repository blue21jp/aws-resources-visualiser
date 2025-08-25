# Ubuntu/macOS開発環境セットアップ

このドキュメントでは、開発に必要なソフトウェアをセットアップする手順を説明します。

## 前提条件

- Ubuntu 24.04 LTS以上 または macOS
- Homebrew導入済み
- mise導入済み（asdfも可能）
- Docker導入済み

## 開発に必要なソフトウェア（事前準備するもの）

### 必須ツール
- **Python 3.13.1** - miseで管理
- **Poetry 2.1.2** - miseで管理
- **make** - ビルド自動化
- **git** - バージョン管理

### AWS関連ツール
- **aws-cli** - AWS操作・認証
- **rain** - CloudFormationデプロイツール
- **cfn-lint** - CloudFormationテンプレート検証

### Docker関連ツール
- **docker** - コンテナ化
- **hadolint** - Dockerfileリンター

### システムツール
- **envsubst** - 環境変数置換（通常はgettext-baseパッケージに含まれる）

## 1. 開発ツールのインストール

### 1.1 AWS CLI v2

```bash
brew install awscli
```

### 1.2 CloudFormation関連ツール

```bash
# rain（CloudFormationデプロイツール）
brew install rain

# cfn-lint（CloudFormationリンター）
brew install cfn-lint

# hadolint（Dockerfileリンター）
brew install hadolint
```

## 2. プロジェクトのセットアップ

### 2.1 リポジトリのクローン

```bash
git clone https://github.com/your-username/aws-resources-visualiser.git
cd aws-resources-visualiser
```

### 2.2 プロジェクト固有のPython環境設定

```bash
# プロジェクトディレクトリで.tool-versionsファイルの確認
cat .tool-versions

# プロジェクト固有のバージョンをインストール（必要に応じて）
mise install
```
