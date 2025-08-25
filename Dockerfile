FROM python:3.13-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とcurlのインストール（ヘルスチェック用）
# hadolint ignore=DL3008,DL3015
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY app/ ./app/
COPY app_web.py .
COPY app_batch.py .

# 非rootユーザーを作成
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# 環境変数の設定（実行時に変更可能な設定）
ENV PYTHONPATH=/app
# ログ設定（開発/本番で変更される可能性がある）
ENV STREAMLIT_LOGGER_LEVEL=info
ENV STREAMLIT_LOGGER_MESSAGE_FORMAT="%(asctime)s [%(levelname)s] %(message)s"
# プライバシー設定（環境によって変更される可能性がある）
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Streamlitのポート8501を公開
EXPOSE 8501

# ヘルスチェックを追加
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Streamlitアプリケーションを起動
# コマンドライン引数：コンテナ環境で固定したい設定
CMD ["streamlit", "run", "app_web.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
