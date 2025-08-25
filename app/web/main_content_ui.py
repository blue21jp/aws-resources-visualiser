#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Resource Visualizer - メインコンテンツUI管理"""

# Standard Library
from typing import Dict, List, Tuple

# Third Party Library
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Local Library
from ..shared.config import (
    CHART_COLORS,
    COST_CALCULATION_INFO,
    COST_DISCLAIMER,
    ESTIMATED_COSTS,
    PAGINATION_CONFIG,
    REQUIRED_TAGS,
)
from .pagination import (
    paginate_dataframe,
    render_pagination_controls,
    render_pagination_info,
)
from .tag_filter import filter_data_by_tags, get_filtered_resource_count


class MainContentUI:
    """メインコンテンツUI管理クラス"""

    def render_data_tabs(
        self,
        selected_services: List[str],
        selected_region: str,
        tag_filters: Dict,
        data: Dict[str, pd.DataFrame],
    ) -> None:
        """データ表示タブをレンダリング"""
        # フィルタが適用されている場合の情報表示
        if tag_filters:
            filtered_counts = get_filtered_resource_count(data, tag_filters)
            total_filtered = sum(filtered_counts.values())
            total_original = sum(len(df) for df in data.values())

            st.info(
                f"🏷️ 必須タグフィルタ適用中: {total_filtered}/{total_original} リソースが条件に一致"
            )

        # タブで各サービスを分離
        tabs = st.tabs(selected_services + ["📈 可視化"])

        # 各サービスのデータを表示
        for i, service in enumerate(selected_services):
            with tabs[i]:
                self._render_service_data_tab(
                    service, selected_region, tag_filters, data
                )

        # 可視化タブ
        with tabs[-1]:
            self._render_visualization_tab(tag_filters, data)

    def _render_service_data_tab(
        self,
        service: str,
        selected_region: str,
        tag_filters: Dict,
        data: Dict[str, pd.DataFrame],
    ) -> None:
        """個別サービスのデータタブをレンダリング"""
        original_data = data.get(service, pd.DataFrame())

        # タグフィルタを適用し、情報を取得
        filtered_data, filter_info = self._apply_tag_filters_and_get_info(
            original_data, tag_filters
        )

        if not filtered_data.empty:
            st.subheader(f"{service} リソース一覧")

            # フィルタ適用時の情報表示
            if (
                tag_filters
                and filter_info["filtered_count"]
                != filter_info["original_count"]
            ):
                st.info(
                    f"📊 フィルタ結果: {filter_info['filtered_count']}/{filter_info['original_count']} リソース"
                )

            # 表示用にTags Dict列を除外（内部処理用のため）
            display_data = filtered_data.drop(
                columns=["Tags Dict"], errors="ignore"
            )

            # ページネーション設定
            page_size = self._render_pagination_settings(service)

            # データをページネーション
            paginated_data, pagination_info = paginate_dataframe(
                display_data,
                page_size=page_size,
                key_prefix=f"{service}_{selected_region}",
            )

            # ページネーション情報を表示
            render_pagination_info(pagination_info)

            # 上部ページネーションコントロール（データが複数ページある場合のみ表示）
            if pagination_info["total_pages"] > 1:
                st.markdown("**📄 ページ操作**")
                render_pagination_controls(
                    pagination_info,
                    key_prefix=f"{service}_{selected_region}",
                    control_id="top",
                )
                st.markdown("---")

            # データ表示（タグコンプライアンスチェック付き）
            self._render_data_with_tag_compliance(display_data, paginated_data)

            # 下部ページネーションコントロール（データが複数ページある場合のみ表示）
            if pagination_info["total_pages"] > 1:
                st.markdown("---")
                render_pagination_controls(
                    pagination_info,
                    key_prefix=f"{service}_{selected_region}",
                    control_id="bottom",
                )

        else:
            st.info(f"{service} リソースが見つかりませんでした")

    def _apply_tag_filters_and_get_info(
        self, original_data: pd.DataFrame, tag_filters: Dict
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """タグフィルタを適用し、フィルタ情報を返す"""
        if tag_filters:
            filtered_data = filter_data_by_tags(original_data, tag_filters)
            filter_info = {
                "filtered_count": len(filtered_data),
                "original_count": len(original_data),
            }
        else:
            filtered_data = original_data
            filter_info = {
                "filtered_count": len(original_data),
                "original_count": len(original_data),
            }

        return filtered_data, filter_info

    def _render_pagination_settings(self, service: str) -> int:
        """ページネーション設定UIをレンダリング"""
        col1, col2 = st.columns([3, 1])
        with col2:
            page_size = st.selectbox(
                "表示件数",
                options=PAGINATION_CONFIG["page_size_options"],
                index=PAGINATION_CONFIG["page_size_options"].index(
                    PAGINATION_CONFIG["default_page_size"]
                ),
                key=f"{service}_page_size",
            )
            return int(page_size)

    def _render_data_with_tag_compliance(
        self, display_data: pd.DataFrame, paginated_data: pd.DataFrame
    ) -> None:
        """タグコンプライアンスチェック付きでデータを表示"""
        if "Required Tags" in display_data.columns:
            # 全体のタグ不足リソース数を計算（フィルタ適用後のデータに対して）
            all_missing_indices = self._get_missing_tag_indices(display_data)

            # 現在のページでのタグ不足リソースを特定
            page_missing_indices = self._get_missing_tag_indices(
                paginated_data
            )

            if all_missing_indices:
                st.warning(
                    f"⚠️ 必須タグ（{', '.join(REQUIRED_TAGS)}）が不足しているリソースが {len(all_missing_indices)} 件あります（赤色で表示）"
                )

                # 表示行数に応じて表の高さを動的に調整
                table_height = min(
                    len(paginated_data) * 35 + 50, 600
                )  # 1行35px + ヘッダー50px、最大600px

                if page_missing_indices:
                    # 現在のページにタグ不足のリソースがある場合、ハイライト表示
                    styled_data = self._highlight_dataframe_rows(
                        paginated_data, page_missing_indices
                    )
                    st.dataframe(
                        styled_data,
                        use_container_width=True,
                        height=table_height,
                    )
                else:
                    # 現在のページにはタグ不足のリソースがない場合
                    st.dataframe(
                        paginated_data,
                        use_container_width=True,
                        height=table_height,
                    )
            else:
                # 表示行数に応じて表の高さを動的に調整
                table_height = min(
                    len(paginated_data) * 35 + 50, 600
                )  # 1行35px + ヘッダー50px、最大600px
                st.success("✅ すべてのリソースに必須タグが設定されています")
                st.dataframe(
                    paginated_data,
                    use_container_width=True,
                    height=table_height,
                )
        else:
            # 表示行数に応じて表の高さを動的に調整
            table_height = min(
                len(paginated_data) * 35 + 50, 600
            )  # 1行35px + ヘッダー50px、最大600px
            st.dataframe(
                paginated_data, use_container_width=True, height=table_height
            )

    def _render_visualization_tab(
        self, tag_filters: Dict, data: Dict[str, pd.DataFrame]
    ) -> None:
        """可視化タブをレンダリング"""
        if data:
            st.subheader("📈 リソース可視化")

            # フィルタが適用されている場合の情報表示
            if tag_filters:
                st.info(
                    "🏷️ 表示されているグラフは必須タグフィルタが適用されたデータに基づいています"
                )

            # フィルタされたデータを準備
            filtered_data = {}
            for service, original_data in data.items():
                filtered_data[service] = (
                    filter_data_by_tags(original_data, tag_filters)
                    if tag_filters
                    else original_data
                )

            # 可視化コンポーネントをレンダリング
            self._render_service_charts(filtered_data)
            self._render_cost_estimation(filtered_data)

    def _render_service_charts(
        self, filtered_data: Dict[str, pd.DataFrame]
    ) -> None:
        """サービス関連のチャートをレンダリング"""
        # 上段：サービス別リソース数とタグコンプライアンス
        col1, col2 = st.columns(2)

        # タグデータを先に計算（フィルタされたデータに基づいて）
        tag_data = {}
        for service, data in filtered_data.items():
            if "Required Tags" in data.columns and not data.empty:
                tagged = len(
                    data[
                        data["Required Tags"].notna()
                        & (data["Required Tags"] != "")
                    ]
                )
                total = len(data)
                tag_data[service] = {
                    "tagged": tagged,
                    "total": total,
                }

        with col1:
            # サービス別リソース数（タグ設定状況で色分け）
            service_counts = {
                service: len(data) for service, data in filtered_data.items()
            }
            if any(count > 0 for count in service_counts.values()):
                if tag_data:
                    # タグ情報がある場合は色分けグラフを使用
                    fig1 = self._create_service_count_with_tags_chart(
                        service_counts, tag_data
                    )
                else:
                    # タグ情報がない場合は従来のグラフを使用
                    fig1 = self._create_service_count_chart(service_counts)
                st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # 全体タグコンプライアンス（円グラフ）
            if tag_data:
                fig2 = self._create_tag_compliance_pie_chart(tag_data)
                st.plotly_chart(fig2, use_container_width=True)

    def _render_cost_estimation(
        self, filtered_data: Dict[str, pd.DataFrame]
    ) -> None:
        """コスト見積もりをレンダリング"""
        # 下段：概算コスト表示
        st.markdown("---")
        st.subheader("💰 概算月額コスト")

        # サービス数を計算
        service_counts = {
            service: len(data) for service, data in filtered_data.items()
        }

        # リソース数が0より大きいサービスのみを対象
        filtered_service_counts = {
            service: count
            for service, count in service_counts.items()
            if count > 0
        }

        if filtered_service_counts:
            fig3 = self._create_cost_estimation_chart(filtered_service_counts)
            st.plotly_chart(fig3, use_container_width=True)

            # 計算詳細を展開可能な形で表示
            self._render_cost_calculation_details(filtered_service_counts)

            # 免責事項を表示
            st.warning(COST_DISCLAIMER)
        else:
            st.info("概算コスト計算対象のリソースがありません")

    def _render_cost_calculation_details(
        self, filtered_service_counts: Dict[str, int]
    ) -> None:
        """コスト計算詳細をレンダリング"""
        with st.expander("📊 概算コスト計算詳細", expanded=False):
            st.markdown("### 計算方法")
            st.markdown("**計算式**: リソース数 × 各サービスの月額想定コスト")

            # 現在のリソースに基づく計算詳細を表示
            st.markdown("### 現在のリソースに基づく計算")
            for service, count in filtered_service_counts.items():
                if service in ESTIMATED_COSTS:
                    cost_per_unit = ESTIMATED_COSTS[service]
                    total_cost = cost_per_unit * count
                    info = COST_CALCULATION_INFO.get(service, "詳細情報なし")

                    st.markdown(
                        f"""
                    **{service}**
                    - リソース数: {count}個
                    - 単価: ${cost_per_unit:.2f}/月
                    - 小計: ${total_cost:.2f}/月 (¥{total_cost * 150:.0f}/月)
                    - 想定: {info}
                    """
                    )

            # 合計金額を表示
            total_usd = sum(
                ESTIMATED_COSTS[service] * count
                for service, count in filtered_service_counts.items()
                if service in ESTIMATED_COSTS
            )
            st.markdown(
                f"""
            ### 合計概算コスト
            **${total_usd:.2f}/月 (¥{total_usd * 150:.0f}/月)**
            """
            )

    # ===== 可視化メソッド =====

    def _create_service_count_chart(
        self, service_counts: Dict[str, int]
    ) -> go.Figure:
        """サービス別リソース数の棒グラフを作成"""
        df = pd.DataFrame(
            list(service_counts.items()), columns=["Service", "Count"]
        )

        fig = px.bar(
            df,
            x="Service",
            y="Count",
            title="サービス別リソース数",
            color="Count",
            color_continuous_scale="viridis",
            text="Count",
        )

        fig.update_traces(
            textposition="inside",
            textfont=dict(color="white", size=12),
            hovertemplate="<b>%{x}</b><br>"
            + "リソース数: %{y}件<br>"
            + "<extra></extra>",
        )

        fig.update_layout(
            xaxis_title="AWSサービス",
            yaxis_title="リソース数",
            showlegend=False,
            plot_bgcolor="white",
        )

        return fig

    def _create_service_count_with_tags_chart(
        self,
        service_counts: Dict[str, int],
        tag_data: Dict[str, Dict[str, int]],
    ) -> go.Figure:
        """サービス別リソース数をタグ設定状況で色分けした棒グラフを作成"""
        services = []
        tagged_counts = []
        untagged_counts = []

        for service, total_count in service_counts.items():
            services.append(service)

            # タグデータがある場合は使用、ない場合は全て未設定として扱う
            if service in tag_data:
                tagged = tag_data[service]["tagged"]
                untagged = tag_data[service]["total"] - tagged
            else:
                tagged = 0
                untagged = total_count

            tagged_counts.append(tagged)
            untagged_counts.append(untagged)

        fig = go.Figure(
            data=[
                go.Bar(
                    name="タグ設定済み",
                    x=services,
                    y=tagged_counts,
                    marker_color=CHART_COLORS["success"],
                    text=tagged_counts,
                    textposition="inside",
                    textfont=dict(color="white", size=12),
                    hovertemplate="<b>%{x}</b><br>"
                    + "タグ設定済み: %{y}件<br>"
                    + "<extra></extra>",
                ),
                go.Bar(
                    name="タグ未設定",
                    x=services,
                    y=untagged_counts,
                    marker_color=CHART_COLORS["danger"],
                    text=untagged_counts,
                    textposition="inside",
                    textfont=dict(color="white", size=12),
                    hovertemplate="<b>%{x}</b><br>"
                    + "タグ未設定: %{y}件<br>"
                    + "<extra></extra>",
                ),
            ]
        )

        fig.update_layout(
            title="サービス別リソース数（タグ設定状況別）",
            xaxis_title="AWSサービス",
            yaxis_title="リソース数",
            barmode="stack",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
        )

        return fig

    def _create_tag_compliance_pie_chart(
        self, tag_data: Dict[str, Dict[str, int]]
    ) -> go.Figure:
        """サービス別タグコンプライアンスの円グラフを作成"""
        if not tag_data:
            return go.Figure().add_annotation(
                text="タグデータがありません",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        # 全体のタグ設定率を計算
        total_resources = sum(data["total"] for data in tag_data.values())
        total_tagged = sum(data["tagged"] for data in tag_data.values())
        total_untagged = total_resources - total_tagged

        if total_resources == 0:
            return go.Figure().add_annotation(
                text="リソースがありません",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        # 円グラフ用のデータを準備
        labels = ["タグ設定済み", "タグ未設定"]
        values = [total_tagged, total_untagged]
        colors = [CHART_COLORS["success"], CHART_COLORS["danger"]]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker_colors=colors,
                    textinfo="label+percent+value",
                    textposition="inside",
                    hovertemplate="<b>%{label}</b><br>"
                    + "リソース数: %{value}<br>"
                    + "割合: %{percent}<br>"
                    + "<extra></extra>",
                )
            ]
        )

        # タグ設定率を計算
        compliance_rate = (
            (total_tagged / total_resources) * 100
            if total_resources > 0
            else 0
        )

        fig.update_layout(
            title=f"全体タグコンプライアンス (設定率: {compliance_rate:.1f}%)",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5,
            ),
        )

        return fig

    def _create_cost_estimation_chart(
        self, resource_counts: Dict[str, int]
    ) -> go.Figure:
        """リソース数に基づく概算コスト表示（参考値）"""
        services = []
        costs = []
        text_labels = []

        for service, count in resource_counts.items():
            if service in ESTIMATED_COSTS and count > 0:
                services.append(service)
                cost = ESTIMATED_COSTS[service] * count
                costs.append(cost)
                # 値をテキストラベルとして追加（USD表示）
                text_labels.append(f"${cost:.2f}")

        if not services:
            return go.Figure().add_annotation(
                text="コスト計算対象のリソースがありません",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        fig = px.bar(
            x=services,
            y=costs,
            title="概算月額コスト（参考値）",
            color=costs,
            color_continuous_scale="reds",
            text=text_labels,  # 棒グラフに値を表示
        )

        fig.update_layout(
            xaxis_title="AWSサービス",
            yaxis_title="概算コスト (USD/月)",
            showlegend=False,
            margin=dict(
                t=80, b=50, l=50, r=50
            ),  # 上部マージンを増やして文字切れを防止
        )

        # テキストラベルの位置とスタイルを調整
        fig.update_traces(
            textposition="inside",  # テキストを棒の内側に表示
            textfont=dict(size=11, color="white"),  # 棒の内側なので白色で統一
            cliponaxis=False,  # 軸の範囲外でもテキストを表示
        )

        return fig

    # ===== ヘルパーメソッド =====

    def _highlight_dataframe_rows(
        self, data: pd.DataFrame, missing_indices: List[int]
    ):
        """DataFrameの指定された行をハイライト"""

        def highlight_row(row):
            if row.name in missing_indices:
                return ["background-color: lightcoral; color: black"] * len(
                    row
                )
            else:
                return [""] * len(row)

        return data.style.apply(highlight_row, axis=1)

    def _get_missing_tag_indices(self, data: pd.DataFrame) -> List[int]:
        """必須タグが不足しているリソースのインデックスを取得"""
        if "Required Tags" not in data.columns:
            return []

        missing_indices = []

        for idx, row in data.iterrows():
            tags_str = row.get("Required Tags", "")
            if pd.isna(tags_str) or tags_str == "":
                missing_indices.append(idx)
                continue

            # タグ文字列から必須タグの存在をチェック
            has_missing_required_tags = False
            for required_tag in REQUIRED_TAGS:
                if required_tag not in str(tags_str):
                    has_missing_required_tags = True
                    break

            if has_missing_required_tags:
                missing_indices.append(idx)

        return missing_indices


# シングルトンインスタンス
_main_content_ui_instance = None


def get_main_content_ui() -> MainContentUI:
    """MainContentUIのシングルトンインスタンスを取得"""
    global _main_content_ui_instance
    if _main_content_ui_instance is None:
        _main_content_ui_instance = MainContentUI()
    return _main_content_ui_instance
