"""
View-Model 映射：将服务层返回的数据映射为前端 DataFrame 及常量列。
"""
from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd

# 列常量
REQ_COLS = ['ID', '请求索引', '状态', '重试次数', '输入Token', '输出Token', '总Token', '开始时间', '结束时间']
ERR_COLS = ['ID', '请求ID', '错误类型', '错误信息', '创建时间']
PERF_COLS = ['平均响应时间(秒)', '总处理时间(秒)', '每秒请求数', '总成本']
TS_COLS = ['time', 'requests', 'success', 'failed']
API_COLS = ['ID', '别名', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活', '创建时间', '更新时间']


def map_requests_df(requests: List[Dict[str, Any]]) -> pd.DataFrame:
    if not requests:
        return pd.DataFrame(columns=REQ_COLS)
    df = pd.DataFrame(requests)
    status_map = {'pending': '等待中', 'processing': '处理中', 'success': '成功', 'failed': '失败', 'retrying': '重试中'}
    if 'status' in df.columns:
        df['status'] = df['status'].map(status_map).fillna(df['status'])
    column_mapping = {
        'id': 'ID',
        'request_index': '请求索引',
        'status': '状态',
        'retry_count': '重试次数',
        'prompt_tokens': '输入Token',
        'completion_tokens': '输出Token',
        'total_tokens': '总Token',
        'start_time': '开始时间',
        'end_time': '结束时间',
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    return df.reindex(columns=REQ_COLS, fill_value='')


def map_errors_df(errors: List[Dict[str, Any]]) -> pd.DataFrame:
    if not errors:
        return pd.DataFrame(columns=ERR_COLS)
    df = pd.DataFrame(errors)
    error_type_map = {
        'api_error': 'API错误',
        'timeout': '超时',
        'rate_limit': '频率限制',
        'system_error': '系统错误',
        'ConfigurationError': '配置错误',
        'ParseError': '解析错误',
        'PerformanceCalculationError': '性能计算错误',
    }
    if 'error_type' in df.columns:
        df['error_type'] = df['error_type'].map(error_type_map).fillna(df['error_type'])
    column_mapping = {
        'id': 'ID',
        'batch_request_id': '请求ID',
        'error_type': '错误类型',
        'error_message': '错误信息',
        'create_time': '创建时间',
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    return df.reindex(columns=ERR_COLS, fill_value='')


def map_performance_df(perf: Dict[str, Any]) -> pd.DataFrame:
    perf = perf or {}
    row = {
        '平均响应时间(秒)': perf.get('avg_response_time'),
        '总处理时间(秒)': perf.get('total_processing_time'),
        '每秒请求数': perf.get('requests_per_second'),
        '总成本': perf.get('total_cost'),
    }
    if all(v is None for v in row.values()):
        return pd.DataFrame(columns=PERF_COLS)
    df = pd.DataFrame([row])
    for col in df.columns:
        if df[col].iloc[0] is not None:
            if '成本' in col:
                df[col] = df[col].apply(lambda x: f"{x:.4f}" if x is not None else '')
            else:
                df[col] = df[col].apply(lambda x: f"{x:.2f}" if x is not None else '')
    return df.reindex(columns=PERF_COLS, fill_value='')


def map_api_detail_df(api: Dict[str, Any]) -> pd.DataFrame:
    api = api or {}
    if not api:
        return pd.DataFrame(columns=API_COLS)
    mapping = {
        'id': 'ID',
        'alias': '别名',
        'api_base': 'API地址',
        'model_name': '模型名称',
        'max_tokens': '最大Token',
        'temperature': '温度',
        'timeout': '超时(秒)',
        'is_active': '是否激活',
        'create_time': '创建时间',
        'update_time': '更新时间',
    }
    row = {mapping[k]: api.get(k) for k in mapping}
    if '是否激活' in row:
        row['是否激活'] = '是' if bool(row['是否激活']) else '否'
    return pd.DataFrame([row]).reindex(columns=API_COLS, fill_value='')
