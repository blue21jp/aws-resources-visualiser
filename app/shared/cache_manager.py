#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - キャッシュマネージャー"""

# Standard Library
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Third Party Library
import pandas as pd
import streamlit as st

# Local Library
from .config import CACHE_DIR, CACHE_TTL


class PersistentCache:
    """ファイルベースの永続キャッシュクラス"""

    def __init__(self, cache_dir: str = CACHE_DIR):
        """キャッシュディレクトリを初期化"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def get_cache_key(
        self, service: str, region: str, profile: Optional[str]
    ) -> str:
        """キャッシュキーを生成"""
        profile_key = profile or "default"
        return f"{service}_{region}_{profile_key}"

    def get_cached_data(
        self,
        service: str,
        region: str,
        profile: Optional[str],
        ttl: int = CACHE_TTL,
    ) -> Optional[pd.DataFrame]:
        """キャッシュからデータを取得"""
        cache_key = self.get_cache_key(service, region, profile)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                stat = cache_file.stat()
                if datetime.now().timestamp() - stat.st_mtime < ttl:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data_dict = json.load(f)
                        return pd.DataFrame(data_dict)
                else:
                    cache_file.unlink(missing_ok=True)
            except Exception as e:
                cache_file.unlink(missing_ok=True)
                st.warning(f"キャッシュファイル読み込みエラー: {e}")

        return None

    def set_cached_data(
        self,
        service: str,
        region: str,
        profile: Optional[str],
        data: pd.DataFrame,
    ) -> bool:
        """データをキャッシュに保存"""
        cache_key = self.get_cache_key(service, region, profile)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            # DataFrameをJSONシリアライズ可能な形式に変換
            data_dict = data.to_dict(orient="records")
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    data_dict, f, ensure_ascii=False, indent=2, default=str
                )
            return True
        except Exception as e:
            st.error(f"キャッシュ保存エラー: {e}")
            return False

    def get_cache_info(
        self, service: str, region: str, profile: Optional[str]
    ) -> Dict[str, str]:
        """キャッシュ情報を取得"""
        cache_key = self.get_cache_key(service, region, profile)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                stat = cache_file.stat()
                current_time = datetime.now().timestamp()
                expires_at = stat.st_mtime + CACHE_TTL

                if current_time < expires_at:
                    expires_datetime = datetime.fromtimestamp(expires_at)
                    fetch_datetime = datetime.fromtimestamp(stat.st_mtime)
                    return {
                        "status": "有効",
                        "expires_at": expires_datetime.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "fetch_time": fetch_datetime.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                else:
                    cache_file.unlink(missing_ok=True)
            except Exception as e:
                cache_file.unlink(missing_ok=True)
                st.warning(f"キャッシュ情報取得エラー: {e}")

        return {"status": "なし", "expires_at": "", "fetch_time": ""}

    def clear_cache(
        self,
        service: Optional[str] = None,
        region: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> int:
        """キャッシュをクリア"""
        cleared_count = 0

        if service and region:
            # 個別のキャッシュファイルを削除
            cache_key = self.get_cache_key(service, region, profile)
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
                cleared_count = 1
        else:
            # 全てのキャッシュファイルを削除
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except Exception as e:
                    st.warning(
                        f"キャッシュファイル削除エラー: {cache_file.name} - {e}"
                    )

        return cleared_count

    def get_cache_size(self) -> Dict[str, Union[int, float]]:
        """キャッシュサイズ情報を取得"""
        total_files = 0
        total_size = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                stat = cache_file.stat()
                total_files += 1
                total_size += stat.st_size
            except Exception as e:
                st.warning(
                    f"キャッシュサイズ取得エラー: {cache_file.name} - {e}"
                )

        return {
            "file_count": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    def get_cache_summary_for_combination(
        self, services: List[str], region: str, profile: Optional[str]
    ) -> Dict[str, Union[int, str, bool]]:
        """指定された組み合わせのキャッシュサマリーを取得"""
        valid_caches = 0
        latest_fetch_time = None
        earliest_expire_time = None

        for service in services:
            cache_info = self.get_cache_info(service, region, profile)
            if cache_info["status"] == "有効":
                valid_caches += 1

                # 最新の取得時刻を記録
                if cache_info["fetch_time"]:
                    try:
                        fetch_time = datetime.strptime(
                            cache_info["fetch_time"], "%Y-%m-%d %H:%M:%S"
                        )
                        if (
                            latest_fetch_time is None
                            or fetch_time > latest_fetch_time
                        ):
                            latest_fetch_time = fetch_time
                    except ValueError:
                        pass

                # 最も早い有効期限を記録
                if cache_info["expires_at"]:
                    try:
                        expire_time = datetime.strptime(
                            cache_info["expires_at"], "%Y-%m-%d %H:%M:%S"
                        )
                        if (
                            earliest_expire_time is None
                            or expire_time < earliest_expire_time
                        ):
                            earliest_expire_time = expire_time
                    except ValueError:
                        pass

        return {
            "total_services": len(services),
            "valid_caches": valid_caches,
            "has_any_cache": valid_caches > 0,
            "latest_fetch_time": (
                latest_fetch_time.strftime("%Y-%m-%d %H:%M:%S")
                if latest_fetch_time
                else ""
            ),
            "earliest_expire_time": (
                earliest_expire_time.strftime("%Y-%m-%d %H:%M:%S")
                if earliest_expire_time
                else ""
            ),
        }


# グローバルキャッシュインスタンス
_cache_instance = None


def get_cache_instance() -> PersistentCache:
    """キャッシュインスタンスを取得（シングルトン）"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PersistentCache()
    return _cache_instance
