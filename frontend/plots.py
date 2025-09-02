"""
Plot 构建工具：集中创建 Plotly 图表。
"""
from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd
import plotly.graph_objects as go


def empty_figure(title: str = '请求/成功/失败 趋势（无数据）') -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title)
    return fig


def build_time_series_from_wide(ts_data: List[Dict[str, Any]]) -> go.Figure:
    """将宽表时间序列（含 time, requests, success, failed 列）绘制成折线图。"""
    if not ts_data:
        return empty_figure()

    ts_cols = ['time', 'requests', 'success', 'failed']
    wide_df = pd.DataFrame(ts_data).reindex(columns=ts_cols, fill_value=0)
    ts_df = pd.melt(
        wide_df,
        id_vars=['time'],
        value_vars=['requests', 'success', 'failed'],
        var_name='metric',
        value_name='value'
    )
    ts_df['value'] = pd.to_numeric(ts_df['value'], errors='coerce').fillna(0)
    ts_df['time'] = pd.to_datetime(ts_df['time'], errors='coerce')
    ts_df = ts_df.sort_values(by=['time', 'metric']).reset_index(drop=True)

    fig = go.Figure()
    colors = {
        'requests': '#6A5ACD',  # SlateBlue
        'success': '#2ECC71',   # Emerald
        'failed': '#FF6B6B',    # Coral Red
    }
    name_map = {'requests': '请求', 'success': '成功', 'failed': '失败'}
    for metric_name, df_g in ts_df.groupby('metric'):
        fig.add_trace(
            go.Scatter(
                x=df_g['time'], y=df_g['value'],
                mode='lines+markers', name=name_map.get(metric_name, metric_name),
                line=dict(color=colors.get(metric_name, None), width=2.5),
                line_shape='spline',
                hovertemplate='%{x}<br>%{fullData.name}: %{y}<extra></extra>'
            )
        )

    try:
        fig.update_traces(showlegend=True)
        if len(fig.data) >= 3:
            if not getattr(fig.data[0], 'name', None):
                fig.data[0].name = '请求'
            if not getattr(fig.data[1], 'name', None):
                fig.data[1].name = '成功'
            if not getattr(fig.data[2], 'name', None):
                fig.data[2].name = '失败'
    except Exception:
        pass

    fig.update_layout(
        template='plotly_white',
        margin=dict(l=40, r=20, t=96, b=64),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.08, xanchor='left', x=0.0,
            bgcolor='rgba(255,255,255,0.85)', bordercolor='#e0e0e0', borderwidth=1
        ),
        showlegend=True,
        hovermode='x unified',
        xaxis=dict(
            type='date',
            showgrid=True, gridcolor='#f0f0f0', zeroline=False,
            rangeslider=dict(visible=True),
            rangeselector=dict(visible=False),
            tickformatstops=[
                dict(dtickrange=[None, 1000], value='%H:%M:%S.%L'),
                dict(dtickrange=[1000, 60000], value='%H:%M:%S'),
                dict(dtickrange=[60000, 86400000], value='%H:%M'),
                dict(dtickrange=[86400000, None], value='%Y-%m-%d')
            ],
        ),
        yaxis=dict(title='数量', showgrid=True, gridcolor='#f0f0f0', zeroline=False),
        title=dict(text='', x=0.0, xanchor='left'),
        transition=dict(duration=300, easing='cubic-in-out'),
        font=dict(family='Inter, PingFang SC, Helvetica, Arial, sans-serif')
    )
    return fig
