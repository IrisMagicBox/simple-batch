"""
UI组件模块，包含各种UI组件的定义和逻辑。
"""

import gradio as gr
import pandas as pd
import asyncio

import service.api_info_service
import service.job_service
import service.ui_response_service
from core.logger import get_logger
from frontend.ui_utils import mask_api_key

logger = get_logger(__name__)


class UIComponents:
    """UI组件类，封装所有UI组件的创建和逻辑。"""
    
    @staticmethod
    def get_api_aliases():
        """获取所有激活的API别名列表。"""
        try:
            aliases = asyncio.run(service.api_info_service.get_active_aliases())
            return aliases
        except Exception as e:
            logger.error(f"获取API别名时出错: {e}")
            return []
    
    @staticmethod
    def refresh_api_configs():
        """刷新API配置表格数据。"""
        try:
            configs = asyncio.run(service.api_info_service.get_all_api_configs_for_ui())
            df = pd.DataFrame(configs)
            if df.empty:
                df = pd.DataFrame(
                    columns=['ID', '别名', 'api_key', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活', '创建时间', '更新时间'])
            else:
                df = df.rename(columns={
                    'id': 'ID',
                    'alias': '别名',
                    'api_key': 'api_key',
                    'api_base': 'API地址',
                    'model_name': '模型名称',
                    'max_tokens': '最大Token',
                    'temperature': '温度',
                    'timeout': '超时(秒)',
                    'is_active': '是否激活',
                    'create_time': '创建时间',
                    'update_time': '更新时间'
                })
                df['是否激活'] = df['是否激活'].map({1: '是', 0: '否', True: '是', False: '否'})
                # 遮蔽API Key：仅遮盖中间12位，保留前4位和后4位；不足长度则全部用*
                if 'api_key' in df.columns:
                    df['api_key'] = df['api_key'].apply(mask_api_key)
                # 仅保留并按指定顺序排列默认字段
                display_columns = ['ID', '别名', 'api_key', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活', '创建时间', '更新时间']
                # 可能后端未返回所有列，使用reindex确保列齐全
                df = df.reindex(columns=display_columns)
            return df
        except Exception as e:
            logger.error(f"刷新API配置时出错: {e}")
            return pd.DataFrame(columns=['ID', '别名', 'api_key', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活', '创建时间', '更新时间'])
    
    @staticmethod
    def refresh_dashboard():
        """刷新仪表盘数据。"""
        try:
            summary = asyncio.run(service.ui_response_service.get_dashboard_summary())
            df = pd.DataFrame(summary)

            if not df.empty:
                df['progress'] = df.apply(
                    lambda row: f"{row.get('success_count', 0) + row.get('failed_count', 0)} / {row.get('total_requests', 0)}",
                    axis=1
                )
                # 显示进行中（非终态）数量，便于理解进度差额
                df['in_progress'] = df.apply(
                    lambda row: max(0, (row.get('total_requests', 0) or 0) - (row.get('success_count', 0) or 0) - (row.get('failed_count', 0) or 0)),
                    axis=1
                )

                status_map = {
                    'pending': '等待中',
                    'processing': '处理中',
                    'completed': '已完成',
                    'failed': '失败',
                    'paused': '已暂停'
                }
                df['status'] = df['status'].map(status_map).fillna(df['status'])

                df = df.rename(columns={
                    'id': 'ID',
                    'batch_name': '任务名称',
                    'status': '状态',
                    'progress': '进度',
                    'in_progress': '进行中',
                    'success_count': '成功数',
                    'failed_count': '失败数',
                    'concurrency': '并发数',
                    'create_time': '创建时间'
                })

                display_columns = ['ID', '任务名称', '状态', '进度', '进行中', '成功数', '失败数', '并发数', '创建时间']
                df_display = df[display_columns]
            else:
                df_display = pd.DataFrame(
                    columns=['ID', '任务名称', '状态', '进度', '成功数', '失败数', '并发数', '创建时间'])
            return df_display
        except Exception as e:
            logger.error(f"刷新仪表盘时出错: {e}")
            return pd.DataFrame(columns=['ID', '任务名称', '状态', '进度', '成功数', '失败数', '并发数', '创建时间'])