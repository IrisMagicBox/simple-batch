"""
UI事件处理模块，包含所有UI交互事件的处理逻辑。
"""

import gradio as gr
import pandas as pd
import asyncio
import plotly.graph_objects as go
import traceback
import json
from typing import Optional

import service.api_info_service
import service.job_service
import service.ui_response_service
import service.export_service
from core.logger import get_logger
from frontend.ui_utils import build_billing_markdown, cap_concurrency_attempts
from frontend.view_models import (
    REQ_COLS, ERR_COLS, PERF_COLS, TS_COLS, API_COLS,
    map_requests_df, map_errors_df, map_performance_df, map_api_detail_df,
)
from frontend.plots import build_time_series_from_wide, empty_figure

logger = get_logger(__name__)


class UIEventHandlers:
    """UI事件处理器类，封装所有UI事件的处理逻辑。"""
    
    @staticmethod
    def on_tab_change():
        """处理Tab切换事件，刷新相关数据。"""
        from frontend.components import UIComponents
        try:
            # 刷新任务仪表盘数据
            dashboard_data = UIComponents.refresh_dashboard()
            # 刷新API配置数据  
            api_configs_data = UIComponents.refresh_api_configs()
            # 刷新API别名下拉框选项
            api_aliases = UIComponents.get_api_aliases()
            
            return dashboard_data, api_configs_data, gr.update(choices=api_aliases)
        except Exception as e:
            logger.error(f"Tab切换时刷新数据失败: {e}")
            # 返回空数据以避免错误
            import pandas as pd
            empty_df = pd.DataFrame()
            return empty_df, empty_df, gr.update(choices=[])
    
    @staticmethod
    def add_api_config_and_refresh(alias, key, base, model, max_tokens, temp, timeout,
                                   currency, prompt_price, completion_price, pricing_notes,
                                   is_active):
        """添加API配置并刷新配置列表（计费字段精简为币种、输入/输出千token单价与备注）。"""
        from frontend.components import UIComponents
        
        if not all([alias, key, base, model]):
            gr.Warning("别名, Key, Base URL 和模型为必填项!")
            return UIComponents.refresh_api_configs()

        try:
            # 转换与默认
            max_tokens_val = int(max_tokens) if max_tokens is not None else 4096
            temp_val = float(temp) if temp is not None else 0.7
            timeout_val = int(timeout) if timeout is not None else 60
            prompt_price_val = float(prompt_price if prompt_price is not None else 0)
            completion_price_val = float(completion_price if completion_price is not None else 0)

            # 校验：非负数
            if prompt_price_val < 0 or completion_price_val < 0:
                gr.Warning("价格必须为非负数！")
                return UIComponents.refresh_api_configs()

            asyncio.run(service.api_info_service.add_api_config(
                alias, key, base, model, max_tokens_val, temp_val, timeout_val,
                str(currency or 'RMB'), 'token',
                prompt_price_val, completion_price_val,
                0.0, 0.0, 1, pricing_notes or None,
                1 if bool(is_active) else 0
            ))
            gr.Info(f"API 配置 '{alias}' 已添加!")
        except Exception as e:
            logger.error(f"添加API配置失败: {e}")
            gr.Error(f"添加API配置失败: {e}")
        return UIComponents.refresh_api_configs()

    @staticmethod
    def open_billing_modal(config_id: Optional[int]):
        """打开计费信息模态框，展示选中的API配置的计费详情。

        返回值:
          - gr.update(visible=True/False) 用于控制模态显示
          - Markdown 文本，展示计费详情
        """
        if not config_id:
            gr.Warning("请先在列表中选择一条API配置后再查看计费信息。")
            return gr.update(visible=False), "未选择配置。请先选择一条配置。"

        try:
            full = asyncio.run(service.api_info_service.get_api_config_by_id(int(config_id))) or {}
            md = build_billing_markdown(full)
            return gr.update(visible=True), md
        except Exception as e:
            logger.error(f"加载计费信息失败: {e}")
            gr.Error(f"加载计费信息失败: {e}")
            return gr.update(visible=False), "加载计费信息失败。"

    @staticmethod
    def copy_api_key_on_click(df: pd.DataFrame, evt: gr.SelectData):
        """当点击API配置表中的api_key列时，返回真实api_key以便前端复制。否则返回空字符串。"""
        try:
            if evt is None or evt.index is None:
                return ""
            # evt.index 可能是 (row_index, col_index)
            row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            col_idx = None
            if isinstance(evt.index, (list, tuple)) and len(evt.index) >= 2:
                col_idx = evt.index[1]
            # 仅当点击的是 api_key 列时触发
            if col_idx is not None:
                cols = list(df.columns)
                if 0 <= col_idx < len(cols) and cols[col_idx] != 'api_key':
                    return ""

            if row_idx is None or df.empty:
                return ""
            row = df.iloc[row_idx]
            config_id = int(row.get('ID')) if 'ID' in df.columns else None
            if not config_id:
                return ""
            full = asyncio.run(service.api_info_service.get_api_config_by_id(int(config_id))) or {}
            return full.get('api_key') or ""
        except Exception as e:
            logger.error(f"复制api_key时出错: {e}")
            return ""
    
    @staticmethod
    def load_api_config_for_edit(df: pd.DataFrame, evt: gr.SelectData):
        """加载选中的API配置到编辑表单（包括计费字段）。"""
        if evt.index is None or df.empty:
            return [None, "", "", "", "", None, None, None,
                    "", None, None, "", False]
        
        try:
            selected_row_index = evt.index[0]
            config = df.iloc[selected_row_index]
            
            # 将"是"/"否"转换回布尔值
            is_active = config['是否激活'] == '是'
            config_id = int(config['ID'])
            # 通过ID获取完整配置（含计费字段）
            full = asyncio.run(service.api_info_service.get_api_config_by_id(config_id)) or {}

            return [
                config_id,
                full.get('alias', config.get('别名')),
                "",  # 不返回API Key，保持为空以保护隐私
                full.get('api_base', config.get('API地址')),
                full.get('model_name', config.get('模型名称')),
                int(full.get('max_tokens') or (config.get('最大Token') if not pd.isna(config.get('最大Token')) else 4096) or 4096),
                float(full.get('temperature') if full.get('temperature') is not None else (config.get('温度') if not pd.isna(config.get('温度')) else 0.7)),
                int(full.get('timeout') if full.get('timeout') is not None else (config.get('超时(秒)') if not pd.isna(config.get('超时(秒)')) else 60)),
                full.get('currency') or 'RMB',
                full.get('prompt_price_per_1k'),
                full.get('completion_price_per_1k'),
                full.get('pricing_notes') or '',
                bool(full.get('is_active') if full.get('is_active') is not None else is_active)
            ]
        except Exception as e:
            logger.error(f"加载API配置到编辑表单时出错: {e}")
            return [None, "", "", "", "", None, None, None,
                    "", None, None, "", False]
    
    @staticmethod
    def update_api_config_and_refresh(config_id, alias, key, base, model, max_tokens, temp, timeout,
                                      currency, prompt_price, completion_price, pricing_notes,
                                      is_active):
        """更新API配置并刷新配置列表（计费字段精简）。"""
        from frontend.components import UIComponents
        
        if not config_id:
            gr.Warning("请先选择一个API配置进行编辑!")
            return UIComponents.refresh_api_configs()
            
        if not all([alias, base, model]):
            gr.Warning("别名, Base URL 和模型为必填项!")
            return UIComponents.refresh_api_configs()

        try:
            updates = {
                'alias': alias,
                'api_base': base,
                'model_name': model,
                'max_tokens': int(max_tokens) if max_tokens else 4096,
                'temperature': float(temp) if temp is not None else 0.7,
                'timeout': int(timeout) if timeout else 60,
                'currency': str(currency) if currency is not None else 'RMB',
                'prompt_price_per_1k': float(prompt_price) if prompt_price is not None else 0.0,
                'completion_price_per_1k': float(completion_price) if completion_price is not None else 0.0,
                'pricing_notes': pricing_notes if pricing_notes is not None else None,
                'is_active': bool(is_active)
            }
            # 强制计费模式为 token
            updates['billing_mode'] = 'token'

            # 校验：非负数
            if updates['prompt_price_per_1k'] < 0 or updates['completion_price_per_1k'] < 0:
                gr.Warning("价格必须为非负数！")
                return UIComponents.refresh_api_configs()
            
            # 只有当用户输入了新的API Key时才更新
            if key:
                updates['api_key'] = key
                
            success = asyncio.run(service.api_info_service.update_api_config_from_ui(config_id, updates))
            if success:
                gr.Info(f"API 配置 '{alias}' 已更新!")
            else:
                gr.Error(f"更新API配置失败!")
        except Exception as e:
            logger.error(f"更新API配置失败: {e}")
            gr.Error(f"更新API配置失败: {e}")
        return UIComponents.refresh_api_configs()
    
    @staticmethod
    def delete_api_config_and_refresh(config_id):
        """删除API配置并刷新配置列表。"""
        from frontend.components import UIComponents
        
        if not config_id:
            gr.Warning("请先选择一个API配置进行删除!")
            return UIComponents.refresh_api_configs()

        try:
            success = asyncio.run(service.api_info_service.delete_api_config_from_ui(config_id))
            if success:
                gr.Info(f"API 配置已删除!")
            else:
                gr.Error(f"删除API配置失败!")
        except ValueError as e:
            logger.error(f"删除API配置失败: {e}")
            gr.Error(f"删除API配置失败: {e}")
        except Exception as e:
            logger.error(f"删除API配置时发生未知错误: {e}")
            gr.Error(f"删除API配置时发生未知错误: {e}")
        return UIComponents.refresh_api_configs()
    
    @staticmethod
    def create_job_and_show_status(file, name, api_alias, concurrency, retries):
        """创建作业并更新状态。"""
        from frontend.components import UIComponents
        
        if file is None or not name or not api_alias:
            gr.Warning("请上传文件、填写任务名称并选择API配置!")
            return gr.skip(), gr.skip()
        try:
            # 并发/重试限制与提示
            concurrency_val, attempts_val, warns = cap_concurrency_attempts(concurrency, retries)
            for w in warns:
                gr.Warning(w)

            job = asyncio.run(service.job_service.create_job_from_file(
                file, name, api_alias, concurrency_val, attempts_val
            ))
            gr.Info(f"任务 '{name}' 已成功创建! Job ID: {job.get('job_id')}")
            return gr.Tabs(selected=1), UIComponents.refresh_dashboard()
        except Exception as e:
            logger.error(f"创建任务失败: {e}", exc_info=True)
            traceback.print_exc()
            gr.Error(f"创建任务失败: {e}")
            return gr.skip(), gr.skip()
    
    @staticmethod
    def show_job_details_and_update_selection(df: pd.DataFrame, evt: gr.SelectData):
        """当用户在仪表盘中选择一行时，显示该作业的详细信息，并更新选中的作业索引。"""
        req_cols = REQ_COLS
        err_cols = ERR_COLS
        perf_cols = PERF_COLS
        ts_cols = TS_COLS
        api_cols = API_COLS

        # 初次选择行时使用默认粒度（例如 1s = 1000ms）。后续通过“应用”按钮刷新更改
        interval_ms = 1000

        if evt.index is None or df.empty:
            # 返回空的DataFrame、空图表和None作为选中的索引
            return (pd.DataFrame(columns=req_cols),
                    pd.DataFrame(columns=err_cols),
                    pd.DataFrame(columns=perf_cols),
                    empty_figure(),
                    pd.DataFrame(columns=api_cols),
                    None)

        try:
            selected_row_index = evt.index[0]
            job_id = int(df.iloc[selected_row_index]['ID'])

            details = asyncio.run(service.ui_response_service.get_job_details_for_ui(job_id))
            if details is None:
                return (pd.DataFrame(columns=req_cols),
                        pd.DataFrame(columns=err_cols),
                        pd.DataFrame(columns=perf_cols),
                        pd.DataFrame(columns=ts_cols),
                        pd.DataFrame(columns=api_cols),
                        selected_row_index)

            # ---------------- 请求表格（分页首页以减少载荷） ----------------
            try:
                page_data = asyncio.run(service.ui_response_service.get_job_requests_page(job_id, page=1, page_size=20))
                req_df = map_requests_df(page_data.get('items', []) or [])
            except Exception:
                req_df = pd.DataFrame(columns=req_cols)

            # ---------------- 错误日志表格 ----------------
            err_df = map_errors_df(details.get('errors', []))

            # ---------------- 性能统计表格 ----------------
            perf_df = map_performance_df(details.get('performance', {}))

            # ---------------- API 配置详情表格 ----------------
            api_df = map_api_detail_df(details.get('api', {}) if isinstance(details, dict) else {})

            # ---------------- 时间序列（折线图） ----------------
            try:
                ts_data = asyncio.run(service.ui_response_service.get_job_time_series_for_ui(job_id, interval_ms))
            except Exception:
                ts_data = []
            if ts_data:
                fig = build_time_series_from_wide(ts_data)
                return (req_df, err_df, perf_df, fig, api_df, selected_row_index)
            else:
                return (req_df, err_df, perf_df, empty_figure(), api_df, selected_row_index)

        except Exception as e:
            logger.error(f"显示作业详情时出错: {e}", exc_info=True)
            return (pd.DataFrame(columns=req_cols),
                    pd.DataFrame(columns=err_cols),
                    pd.DataFrame(columns=perf_cols),
                    empty_figure(),
                    pd.DataFrame(columns=api_cols),
                    None)

    @staticmethod
    def refresh_time_series_only(df: pd.DataFrame, selected_index: int, interval: str):
        """仅刷新时间序列折线图，用于切换间隔后不更改其他表格。"""
        ts_cols = ['time', 'requests', 'success', 'failed']

        def _interval_to_ms(val: str) -> int:
            if not val:
                return 1000
            val = str(val).strip().lower()
            try:
                if val.endswith('ms'):
                    return max(1, int(val[:-2]))
                if val.endswith('s'):
                    return max(1, int(float(val[:-1]) * 1000))
                if val.endswith('min'):
                    return max(1, int(float(val[:-3]) * 60_000))
                return max(1, int(float(val)))
            except Exception:
                return 1000

        if df is None or df.empty or selected_index is None or selected_index >= len(df):
            return empty_figure()

        try:
            job_id = int(df.iloc[selected_index]['ID'])
            interval_ms = _interval_to_ms(interval)
            ts_data = asyncio.run(service.ui_response_service.get_job_time_series_for_ui(job_id, interval_ms))
        except Exception:
            ts_data = []

        if ts_data:
            return build_time_series_from_wide(ts_data)
        else:
            return empty_figure()

    @staticmethod
    def _safe_to_markdown(val):
        """将任意值安全转换为可显示的字符串或保持为 JSON 结构。"""
        if val is None:
            return ""
        # 对于字符串直接返回
        if isinstance(val, str):
            return val
        # 其他可序列化对象转为缩进的 JSON 字符串
        try:
            return json.dumps(val, ensure_ascii=False, indent=2)
        except Exception:
            return str(val)

    @staticmethod
    def _pretty_json_str(val: str) -> str:
        """如果是JSON字符串则美化为多行，否则原样返回。"""
        if not isinstance(val, str) or not val:
            return val or ""
        try:
            parsed = json.loads(val)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            return val

    @staticmethod
    def load_request_page(dashboard_df: pd.DataFrame, selected_job_index, current_page):
        """加载请求内容分页（每页2条）。返回：
        page_info_md, md1_summary, messages1(JSON), response1(str), md2_summary, messages2(JSON), response2(str), current_page(int)
        """
        # 基本校验
        if dashboard_df is None or len(dashboard_df) == 0 or selected_job_index is None:
            return ("", "", None, "", "", None, "", 1)
        try:
            job_id = int(dashboard_df.iloc[int(selected_job_index)]['ID'])
        except Exception:
            return ("", "", None, "", "", None, "", 1)

        try:
            page = int(current_page) if current_page else 1
            data = asyncio.run(service.ui_response_service.get_job_requests_page(job_id, page, page_size=2))
        except Exception as e:
            logger.error(f"加载请求分页数据失败: {e}", exc_info=True)
            return ("", "", None, "", "", None, "", 1)

        items = data.get('items', []) or []
        page = data.get('page', 1)
        total = data.get('total', 0)
        total_pages = data.get('total_pages', 1)
        page_info_md = f"第 {page}/{total_pages} 页，共 {total} 条请求"

        # 准备两条数据
        if len(items) >= 1:
            i1 = items[0]
            msg1 = i1.get('messages')
            resp1_raw = i1.get('response_body')
            # 优先将单行JSON字符串美化为多行
            resp1 = UIEventHandlers._pretty_json_str(resp1_raw) if isinstance(resp1_raw, str) else UIEventHandlers._safe_to_markdown(resp1_raw)
            md1 = f"请求 #{i1.get('request_index', '-')} · 状态：{i1.get('status', '')}"
        else:
            msg1, resp1, md1 = None, "", ""
        if len(items) >= 2:
            i2 = items[1]
            msg2 = i2.get('messages')
            resp2_raw = i2.get('response_body')
            resp2 = UIEventHandlers._pretty_json_str(resp2_raw) if isinstance(resp2_raw, str) else UIEventHandlers._safe_to_markdown(resp2_raw)
            md2 = f"请求 #{i2.get('request_index', '-')} · 状态：{i2.get('status', '')}"
        else:
            msg2, resp2, md2 = None, "", ""

        return (page_info_md, md1, msg1, resp1, md2, msg2, resp2, page)

    @staticmethod
    def load_requests_table_page(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """分页加载“请求详情”表格。返回：requests_df(DataFrame), req_page_info_md(str), current_page(int)
        page_size 支持 20/50/100。
        """
        req_cols = REQ_COLS
        if dashboard_df is None or len(dashboard_df) == 0 or selected_job_index is None:
            return (pd.DataFrame(columns=req_cols), "", 1)
        try:
            job_id = int(dashboard_df.iloc[int(selected_job_index)]['ID'])
        except Exception:
            return (pd.DataFrame(columns=req_cols), "", 1)

        try:
            page = int(current_page) if current_page else 1
            size = int(page_size) if page_size else 20
            if size not in (20, 50, 100):
                size = 20
            data = asyncio.run(service.ui_response_service.get_job_requests_page(job_id, page=page, page_size=size))
        except Exception as e:
            logger.error(f"加载请求表格分页失败: {e}", exc_info=True)
            return (pd.DataFrame(columns=req_cols), "", 1)

        items = data.get('items', []) or []
        page = data.get('page', 1)
        total = data.get('total', 0)
        total_pages = data.get('total_pages', 1)
        req_df = map_requests_df(items)
        page_info_md = f"第 {page}/{total_pages} 页，共 {total} 条请求"
        return (req_df, page_info_md, page)

    @staticmethod
    def requests_table_prev(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """请求表格上一页"""
        try:
            p = int(current_page) if current_page else 1
            new_page = max(1, p - 1)
        except Exception:
            new_page = 1
        return UIEventHandlers.load_requests_table_page(dashboard_df, selected_job_index, new_page, page_size)

    @staticmethod
    def requests_table_next(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """请求表格下一页"""
        try:
            p = int(current_page) if current_page else 1
            new_page = p + 1
        except Exception:
            new_page = 1
        return UIEventHandlers.load_requests_table_page(dashboard_df, selected_job_index, new_page, page_size)

    @staticmethod
    def requests_table_change_page_size(dashboard_df: pd.DataFrame, selected_job_index, page_size):
        """修改每页大小时，回到第1页并刷新"""
        return UIEventHandlers.load_requests_table_page(dashboard_df, selected_job_index, 1, page_size)

    @staticmethod
    def requests_table_jump(dashboard_df: pd.DataFrame, selected_job_index, jump_page, page_size):
        """跳转到指定页码（后端会做边界修正）"""
        try:
            page = int(jump_page) if jump_page else 1
            if page < 1:
                page = 1
        except Exception:
            page = 1
        return UIEventHandlers.load_requests_table_page(dashboard_df, selected_job_index, page, page_size)

    @staticmethod
    def load_errors_table_page(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """分页加载“错误日志”表格。返回：errors_df(DataFrame), err_page_info_md(str), current_page(int)
        page_size 支持 20/50/100。
        """
        err_cols = ERR_COLS
        if dashboard_df is None or len(dashboard_df) == 0 or selected_job_index is None:
            return (pd.DataFrame(columns=err_cols), "", 1)
        try:
            job_id = int(dashboard_df.iloc[int(selected_job_index)]['ID'])
        except Exception:
            return (pd.DataFrame(columns=err_cols), "", 1)

        try:
            page = int(current_page) if current_page else 1
            size = int(page_size) if page_size else 20
            if size not in (20, 50, 100):
                size = 20
            data = asyncio.run(service.ui_response_service.get_job_errors_page(job_id, page=page, page_size=size))
        except Exception as e:
            logger.error(f"加载错误日志表格分页失败: {e}", exc_info=True)
            return (pd.DataFrame(columns=err_cols), "", 1)

        items = data.get('items', []) or []
        page = data.get('page', 1)
        total = data.get('total', 0)
        total_pages = data.get('total_pages', 1)
        err_df = map_errors_df(items)
        page_info_md = f"第 {page}/{total_pages} 页，共 {total} 条错误"
        return (err_df, page_info_md, page)

    @staticmethod
    def errors_table_prev(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """错误表格上一页"""
        try:
            p = int(current_page) if current_page else 1
            new_page = max(1, p - 1)
        except Exception:
            new_page = 1
        return UIEventHandlers.load_errors_table_page(dashboard_df, selected_job_index, new_page, page_size)

    @staticmethod
    def errors_table_next(dashboard_df: pd.DataFrame, selected_job_index, current_page, page_size):
        """错误表格下一页"""
        try:
            p = int(current_page) if current_page else 1
            new_page = p + 1
        except Exception:
            new_page = 1
        return UIEventHandlers.load_errors_table_page(dashboard_df, selected_job_index, new_page, page_size)

    @staticmethod
    def errors_table_change_page_size(dashboard_df: pd.DataFrame, selected_job_index, page_size):
        """修改每页大小时，回到第1页并刷新（错误日志）"""
        return UIEventHandlers.load_errors_table_page(dashboard_df, selected_job_index, 1, page_size)

    @staticmethod
    def errors_table_jump(dashboard_df: pd.DataFrame, selected_job_index, jump_page, page_size):
        """跳转到指定页码（错误日志）"""
        try:
            page = int(jump_page) if jump_page else 1
            if page < 1:
                page = 1
        except Exception:
            page = 1
        return UIEventHandlers.load_errors_table_page(dashboard_df, selected_job_index, page, page_size)

    @staticmethod
    def request_page_prev(dashboard_df: pd.DataFrame, selected_job_index, current_page):
        """上一页：页码-1，最小为1。"""
        new_page = 1
        try:
            p = int(current_page) if current_page else 1
            new_page = max(1, p - 1)
        except Exception:
            new_page = 1
        # 复用加载函数
        return UIEventHandlers.load_request_page(dashboard_df, selected_job_index, new_page)

    @staticmethod
    def request_page_next(dashboard_df: pd.DataFrame, selected_job_index, current_page):
        """下一页：页码+1，并不越界（在 load 中会被服务端总页数校正）。"""
        try:
            p = int(current_page) if current_page else 1
            new_page = p + 1
        except Exception:
            new_page = 1
        return UIEventHandlers.load_request_page(dashboard_df, selected_job_index, new_page)

    @staticmethod
    def show_request_selection(evt: gr.SelectData):
        """处理请求表格的选择事件"""
        if evt.index is None:
            return None
        return evt.index[0]

    @staticmethod
    def clear_selected_request_detail():
        """当切换作业时，清空单条请求详情及所选请求索引。"""
        return ("", None, "", None)

    @staticmethod
    def load_request_detail_by_evt(requests_df: pd.DataFrame, evt: gr.SelectData):
        """在请求列表中选中一行时，加载该请求的详情（单条）。
        返回：req_detail_md(str), req_messages_json(obj), req_response_code(str)
        """
        # 默认空返回
        empty = ("", None, "")
        try:
            if evt is None or evt.index is None or requests_df is None or len(requests_df) == 0:
                return empty
            row_idx = evt.index[0]
            if row_idx is None or row_idx >= len(requests_df):
                return empty
            # 取出请求ID
            request_id = int(requests_df.iloc[row_idx]['ID'])
        except Exception:
            return empty

        try:
            data = asyncio.run(service.ui_response_service.get_request_detail(request_id))
            if not data:
                return empty
            # 摘要Markdown
            md = (
                f"**请求ID**: {data.get('id','')}  |  "
                f"**索引**: {data.get('request_index','')}  |  "
                f"**状态**: {data.get('status','')}  |  "
                f"**重试**: {data.get('retry_count','')}  |  "
                f"**Tokens**: prompt={data.get('prompt_tokens','')}, completion={data.get('completion_tokens','')}, total={data.get('total_tokens','')}  |  "
                f"**开始**: {data.get('start_time','')}  |  **结束**: {data.get('end_time','')}"
            )
            # messages 已在CURD层解析为对象（若失败则可能是字符串）
            messages = data.get('messages')
            # response 友好换行/美化
            resp_raw = data.get('response_body')
            resp = UIEventHandlers._pretty_json_str(resp_raw) if isinstance(resp_raw, str) else UIEventHandlers._safe_to_markdown(resp_raw)
            return (md, messages, resp)
        except Exception as e:
            logger.error(f"加载请求详情失败: {e}", exc_info=True)
            return empty

    @staticmethod
    def load_first_request_detail(df: pd.DataFrame, evt: gr.SelectData):
        """当切换作业时，自动加载该作业请求列表中的第一条详情。
        返回：req_detail_md(str), req_messages_json(obj), req_response_code(str), selected_request_index(int)
        若无请求则清空。
        """
        empty = ("", None, "", None)
        try:
            if evt is None or evt.index is None or df is None or len(df) == 0:
                return empty
            selected_row_index = evt.index[0]
            job_id = int(df.iloc[selected_row_index]['ID'])
        except Exception:
            return empty

        try:
            data = asyncio.run(service.ui_response_service.get_job_requests_page(job_id, page=1, page_size=1))
            items = (data or {}).get('items', [])
            if not items:
                return empty
            i = items[0]
            md = (
                f"**请求ID**: {i.get('id','')}  |  "
                f"**索引**: {i.get('request_index','')}  |  "
                f"**状态**: {i.get('status','')}  |  "
                f"**重试**: {i.get('retry_count','')}  |  "
                f"**Tokens**: prompt={i.get('prompt_tokens','')}, completion={i.get('completion_tokens','')}, total={i.get('total_tokens','')}  |  "
                f"**开始**: {i.get('start_time','')}  |  **结束**: {i.get('end_time','')}"
            )
            messages = i.get('messages')
            resp_raw = i.get('response_body')
            resp = UIEventHandlers._pretty_json_str(resp_raw) if isinstance(resp_raw, str) else UIEventHandlers._safe_to_markdown(resp_raw)
            # 默认选中第一条
            return (md, messages, resp, 0)
        except Exception as e:
            logger.error(f"加载首条请求详情失败: {e}", exc_info=True)
            return empty

    @staticmethod
    def open_time_bucket_modal(df: pd.DataFrame, selected_index: int, interval: str, bucket_str: str):
        """打开时间桶详情模态，默认加载失败(failed)类别的首条记录。
        返回: (modal_vis, title_md, count_md, messages, response_code, items_state, index_state, category_state, bucket_state)
        """
        # 默认：隐藏模态与空内容
        hidden = (gr.update(visible=False), "", "", None, "", [], 0, "failed", "")

        # 解析 interval
        def _interval_to_ms(val: str) -> int:
            if not val:
                return 1000
            v = str(val).strip().lower()
            try:
                if v.endswith('ms'):
                    return max(1, int(v[:-2]))
                if v.endswith('s'):
                    return max(1, int(float(v[:-1]) * 1000))
                if v.endswith('min'):
                    return max(1, int(float(v[:-3]) * 60_000))
                return max(1, int(float(v)))
            except Exception:
                return 1000

        # 解析桶字符串为对齐后的键
        def _normalize_bucket(s: str, interval_ms: int) -> Optional[str]:
            try:
                ts = pd.to_datetime(s, errors='coerce')
                if pd.isna(ts):
                    return None
                # floor 到间隔
                epoch = pd.Timestamp('1970-01-01', tz=ts.tz)
                delta_ms = int((ts - epoch).total_seconds() * 1000)
                floored = (delta_ms // interval_ms) * interval_ms
                floored_ts = epoch + pd.to_timedelta(floored, unit='ms')
                # 与 CURD 层相同的格式
                if interval_ms < 1000:
                    return floored_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                elif interval_ms < 60000:
                    return floored_ts.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return floored_ts.strftime('%Y-%m-%d %H:%M')
            except Exception:
                return None

        try:
            if df is None or df.empty or selected_index is None or selected_index >= len(df):
                return hidden
            job_id = int(df.iloc[selected_index]['ID'])
            interval_ms = _interval_to_ms(interval)
            bucket = _normalize_bucket(bucket_str, interval_ms)
            if not bucket:
                return hidden

            items = asyncio.run(service.ui_response_service.get_requests_by_time_bucket(job_id, bucket, interval_ms, 'failed')) or []
            title = f"#### 时间点 {bucket} | 类别: 失败"
            count_md = f"共 {len(items)} 条"
            if not items:
                return (gr.update(visible=True), title, count_md, None, "", items, 0, 'failed', bucket)

            idx = 0
            cur = items[idx]
            messages = cur.get('messages')
            resp_raw = cur.get('response_body')
            resp = UIEventHandlers._pretty_json_str(resp_raw) if isinstance(resp_raw, str) else UIEventHandlers._safe_to_markdown(resp_raw)
            return (gr.update(visible=True), title, count_md, messages, resp, items, idx, 'failed', bucket)
        except Exception as e:
            logger.error(f"打开时间桶模态失败: {e}", exc_info=True)
            return hidden

    @staticmethod
    def load_time_bucket_by_category(df: pd.DataFrame, selected_index: int, interval: str, bucket_str: str, category: str):
        """在模态内切换类别：category in ['failed','requests','success']。
        返回: (title_md, count_md, messages, response_code, items_state, index_state, category_state)
        """
        def _interval_to_ms(val: str) -> int:
            if not val:
                return 1000
            v = str(val).strip().lower()
            try:
                if v.endswith('ms'):
                    return max(1, int(v[:-2]))
                if v.endswith('s'):
                    return max(1, int(float(v[:-1]) * 1000))
                if v.endswith('min'):
                    return max(1, int(float(v[:-3]) * 60_000))
                return max(1, int(float(v)))
            except Exception:
                return 1000

        def _normalize_bucket(s: str, interval_ms: int) -> Optional[str]:
            try:
                ts = pd.to_datetime(s, errors='coerce')
                if pd.isna(ts):
                    return None
                epoch = pd.Timestamp('1970-01-01', tz=ts.tz)
                delta_ms = int((ts - epoch).total_seconds() * 1000)
                floored = (delta_ms // interval_ms) * interval_ms
                floored_ts = epoch + pd.to_timedelta(floored, unit='ms')
                if interval_ms < 1000:
                    return floored_ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                elif interval_ms < 60000:
                    return floored_ts.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return floored_ts.strftime('%Y-%m-%d %H:%M')
            except Exception:
                return None

        try:
            if df is None or df.empty or selected_index is None or selected_index >= len(df):
                return ("", "", None, "", [], 0, "failed")
            job_id = int(df.iloc[selected_index]['ID'])
            interval_ms = _interval_to_ms(interval)
            bucket = _normalize_bucket(bucket_str, interval_ms)
            if not bucket:
                return ("", "", None, "", [], 0, "failed")
            cat = category if category in ('failed','requests','success') else 'failed'
            items = asyncio.run(service.ui_response_service.get_requests_by_time_bucket(job_id, bucket, interval_ms, cat)) or []
            title = f"#### 时间点 {bucket} | 类别: {'失败' if cat=='failed' else ('请求' if cat=='requests' else '成功')}"
            count_md = f"共 {len(items)} 条"
            if not items:
                return (title, count_md, None, "", items, 0, cat)
            idx = 0
            cur = items[idx]
            messages = cur.get('messages')
            resp_raw = cur.get('response_body')
            resp = UIEventHandlers._pretty_json_str(resp_raw) if isinstance(resp_raw, str) else UIEventHandlers._safe_to_markdown(resp_raw)
            return (title, count_md, messages, resp, items, idx, cat)
        except Exception as e:
            logger.error(f"加载时间桶类别失败: {e}", exc_info=True)
            return ("", "", None, "", [], 0, "failed")

    @staticmethod
    def change_time_bucket_index(
        df: pd.DataFrame,
        selected_index: int,
        interval: str,
        bucket_str: str,
        items: list,
        cur_index: int,
        category: str,
        bucket_state: str,
        delta: int,
    ):
        """上一条/下一条。使用已有 items 列表在前端分页。
        返回: (title_md, count_md, messages, response_code, new_index)
        """
        try:
            if not isinstance(items, list) or len(items) == 0:
                return ("", "", None, "", 0)
            n = len(items)
            idx = int(cur_index or 0) + int(delta or 0)
            if idx < 0:
                idx = 0
            if idx >= n:
                idx = n - 1
            cur = items[idx]
            bucket = bucket_state or bucket_str or ""
            title = f"#### 时间点 {bucket} | 类别: {'失败' if category=='failed' else ('请求' if category=='requests' else '成功')} | {idx+1}/{n}"
            count_md = f"共 {n} 条"
            messages = cur.get('messages')
            resp_raw = cur.get('response_body')
            resp = UIEventHandlers._pretty_json_str(resp_raw) if isinstance(resp_raw, str) else UIEventHandlers._safe_to_markdown(resp_raw)
            return (title, count_md, messages, resp, idx)
        except Exception as e:
            logger.error(f"翻页失败: {e}", exc_info=True)
            return ("", "", None, "", int(cur_index or 0))

    @staticmethod
    def delete_job(df: pd.DataFrame, selected_index: int):
        """删除指定的作业"""
        from frontend.components import UIComponents
        
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行删除!")
            return UIComponents.refresh_dashboard()
        
        try:
            job_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.delete_job(job_id))
            if success:
                gr.Info(f"作业 {job_id} 已成功删除!")
            else:
                gr.Error(f"删除作业 {job_id} 失败!")
        except Exception as e:
            logger.error(f"删除作业时发生错误: {e}")
            gr.Error(f"删除作业时发生错误: {e}")
        return UIComponents.refresh_dashboard()
    
    @staticmethod
    def retry_failed_requests(df: pd.DataFrame, selected_index: int):
        """重试指定作业的所有失败请求"""
        from frontend.components import UIComponents
        
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行重试!")
            return UIComponents.refresh_dashboard()
        
        try:
            job_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.retry_failed_requests(job_id))
            if success:
                gr.Info(f"作业 {job_id} 的失败请求已重置为待处理状态!")
            else:
                gr.Error(f"重试作业 {job_id} 的失败请求失败!")
        except Exception as e:
            logger.error(f"重试作业失败请求时发生错误: {e}")
            gr.Error(f"重试作业失败请求时发生错误: {e}")
        return UIComponents.refresh_dashboard()
    
    @staticmethod
    def reset_job(df: pd.DataFrame, selected_index: int):
        """重置指定作业为待处理状态"""
        from frontend.components import UIComponents
        
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行重试!")
            return UIComponents.refresh_dashboard()
        
        try:
            job_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.reset_job_to_pending(job_id))
            if success:
                gr.Info(f"作业 {job_id} 已重置为待处理状态!")
            else:
                gr.Error(f"重置作业 {job_id} 失败!")
        except Exception as e:
            logger.error(f"重置作业时发生错误: {e}")
            gr.Error(f"重置作业时发生错误: {e}")
        return UIComponents.refresh_dashboard()
    
    @staticmethod
    def pause_job(df: pd.DataFrame, selected_index: int):
        """暂停指定作业"""
        from frontend.components import UIComponents
        
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行暂停!")
            return UIComponents.refresh_dashboard()
        
        try:
            job_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.pause_job(job_id))
            if success:
                gr.Info(f"作业 {job_id} 已暂停")
            else:
                gr.Error(f"暂停作业 {job_id} 失败!")
        except Exception as e:
            logger.error(f"暂停作业时发生错误: {e}")
            gr.Error(f"暂停作业时发生错误: {e}")
        return UIComponents.refresh_dashboard()

    @staticmethod
    def resume_job(df: pd.DataFrame, selected_index: int):
        """恢复指定作业"""
        from frontend.components import UIComponents
        
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行恢复!")
            return UIComponents.refresh_dashboard()
        
        try:
            job_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.resume_job(job_id))
            if success:
                gr.Info(f"作业 {job_id} 已恢复")
            else:
                gr.Error(f"恢复作业 {job_id} 失败!")
        except Exception as e:
            logger.error(f"重试请求时发生错误: {e}")
            gr.Error(f"重试请求时发生错误: {e}")
        return UIComponents.refresh_dashboard()
    
    @staticmethod
    def retry_request(df: pd.DataFrame, selected_index: int):
        """重试指定的单个请求"""
        from frontend.components import UIComponents
        
        if selected_index is None or df is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个请求进行重试!")
            return UIComponents.refresh_dashboard()
        
        try:
            request_id = int(df.iloc[selected_index]['ID'])
            success = asyncio.run(service.job_service.retry_specific_request(request_id))
            if success:
                gr.Info(f"请求 {request_id} 已重置为待处理状态!")
            else:
                gr.Error(f"重试请求 {request_id} 失败!")
        except Exception as e:
            logger.error(f"重试请求时发生错误: {e}")
            gr.Error(f"重试请求时发生错误: {e}")
        return UIComponents.refresh_dashboard()
    
    @staticmethod
    def export_job_results(df: pd.DataFrame, selected_index: int):
        """导出指定作业的结果"""
        if selected_index is None or df.empty or selected_index >= len(df):
            gr.Warning("请选择一个作业进行导出!")
            return gr.update(visible=False, value=None)
        
        try:
            selected_row = df.iloc[selected_index]
            job_id = int(selected_row['ID'])
            batch_name = selected_row['任务名称']
            
            # 执行导出
            filename = asyncio.run(service.export_service.export_job_results_to_json(job_id, batch_name))
            gr.Info(f"作业 '{batch_name}' 的结果已导出到: {filename}。您也可以点击下方链接直接下载。")
            # 返回给 File 组件以触发浏览器下载
            return gr.update(value=filename, visible=True)
        except Exception as e:
            logger.error(f"导出作业结果时发生错误: {e}")
            gr.Error(f"导出作业结果时发生错误: {e}")
            return gr.update(visible=False, value=None)