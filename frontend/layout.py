"""
UI布局模块，包含Gradio UI的布局定义。
"""

import gradio as gr
from frontend.components import UIComponents
from frontend.event_handlers import UIEventHandlers


def create_ui_layout():
    """创建UI布局。"""
    with gr.Blocks(title="OpenAI Batch Processor", theme=gr.themes.Soft()) as app:
        gr.Markdown("## LLM Simple Batch")

        # 全局样式：模态与遮罩
        gr.HTML(
            """
            <style>
            .api-modal { position: fixed; inset: 0; z-index: 99990; background: transparent !important; pointer-events: none; }
            .api-modal-backdrop { position: fixed; inset: 0; z-index: 99990; background: rgba(0,0,0,0.12); backdrop-filter: blur(1px); pointer-events: none; }
            .api-modal .modal-content { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                z-index: 99999; pointer-events: auto; background: var(--block-background-fill, #fff); color: inherit;
                width: min(960px, 96vw); border-radius: 14px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                padding: 18px; max-height: 88vh; overflow: auto; border: 1px solid var(--block-border-color, #eee); }
            .api-modal .modal-content * { pointer-events: auto; }
            .api-modal .modal-footer { display: flex; gap: 8px; justify-content: flex-end; }
            /* 强制模型名称输入框可见（防止被样式/布局影响隐藏）*/
            #model_name_input, #edit_model_name_input { display: block !important; visibility: visible !important; }
            #model_name_input .wrap, #edit_model_name_input .wrap { display: block !important; }
            #model_name_input .container, #edit_model_name_input .container { display: block !important; }
            /* 强制模态内容区域为纯白背景，去除灰色块 */
            .api-modal .modal-content,
            .api-modal .modal-content .block,
            .api-modal .modal-content .form,
            .api-modal .modal-content .wrap,
            .api-modal .modal-content .panel,
            .api-modal .modal-content .container,
            .api-modal .modal-content .gradio-container,
            .api-modal .modal-content .gradio-row,
            .api-modal .modal-content .gradio-column,
            .api-modal .modal-content .label-wrap,
            .api-modal .modal-content pre,
            .api-modal .modal-content code,
            .api-modal .modal-content .cm-editor,
            .api-modal .modal-content .cm-scroller,
            .api-modal .modal-content .cm-content,
            .api-modal .modal-content .cm-gutters,
            .api-modal .modal-content .svelte-jsoneditor,
            .api-modal .modal-content .svelte-jsoneditor-tree,
            .api-modal .modal-content .svelte-jsoneditor-menu,
            .api-modal .modal-content .svelte-jsoneditor-context-menu,
            .api-modal .modal-content .svelte-jsoneditor-statusbar,
            #time_bucket_modal .modal-footer {
                background: #fff !important;
                box-shadow: none !important;
            }
            /* 保险：模态内所有子元素背景都设为白色，避免遗留灰块 */
            #time_bucket_modal .modal-content, 
            #time_bucket_modal .modal-content * {
                background-color: #fff !important;
            }
            /* 去掉可能导致灰线的边框/阴影 */
            #time_bucket_modal .modal-content, 
            #time_bucket_modal .modal-content * {
                border-color: transparent !important;
                box-shadow: none !important;
            }
            /* 修复 JSON 编辑器底部和 CodeMirror 高亮产生的灰色 */
            #time_bucket_modal .cm-activeLine,
            #time_bucket_modal .cm-tooltip,
            #time_bucket_modal .cm-tooltip * {
                background: #fff !important;
            }
            /* 修复 JSON/Code 编辑器滚动条交汇处灰色角块 */
            #time_bucket_modal ::-webkit-scrollbar-corner { background: #fff !important; }
            #time_bucket_modal ::-webkit-scrollbar-track { background: #fff !important; }
            /* Firefox */
            #time_bucket_modal { scrollbar-color: auto; }
            #time_bucket_modal .cm-editor, 
            #time_bucket_modal .svelte-jsoneditor { scrollbar-color: auto; }
            /* 按钮之间区域也保持白色 */
            #time_bucket_modal .modal-footer .gradio-row,
            #time_bucket_modal .modal-footer .gradio-column,
            #time_bucket_modal .modal-footer .block,
            #time_bucket_modal .modal-footer .form,
            #time_bucket_modal .modal-footer > * { background: #fff !important; }
            /* 移除按钮周围可能的阴影/边框造成的灰色感 */
            #time_bucket_modal .modal-footer button { box-shadow: none !important; background-image: none !important; }
            /* 确保所有模态框的按钮区域背景为白色 */
            .api-modal .modal-footer { background: #fff !important; }
            .api-modal .modal-footer .gradio-row,
            .api-modal .modal-footer .gradio-column,
            .api-modal .modal-footer .block,
            .api-modal .modal-footer .form,
            .api-modal .modal-footer > * { background: #fff !important; }
            /* 移除所有模态框按钮周围可能的阴影/边框造成的灰色感 */
            .api-modal .modal-footer button { box-shadow: none !important; background-image: none !important; }
            /* 时间桶模态框中的按钮配色 - 稍微鲜艳一点但仍保持柔和 */
            #btn-tb-failed, #time_bucket_modal .btn-tb-failed { 
                background: #ff7f7f !important; 
                border-color: #ff7f7f !important; 
                color: white !important;
                background-image: none !important;
            }
            #btn-tb-requests, #time_bucket_modal .btn-tb-requests { 
                background: #6495ed !important; 
                border-color: #6495ed !important; 
                color: white !important;
                background-image: none !important;
            }
            #btn-tb-success, #time_bucket_modal .btn-tb-success { 
                background: #66cdaa !important; 
                border-color: #66cdaa !important; 
                color: white !important;
                background-image: none !important;
            }
            #btn-tb-prev, #time_bucket_modal .btn-tb-prev,
            #btn-tb-next, #time_bucket_modal .btn-tb-next { 
                background: #6495ed !important; 
                border-color: #6495ed !important; 
                color: white !important;
                background-image: none !important;
            }
            /* 圆角化时间桶模态内的按钮 */
            #btn-tb-failed,
            #btn-tb-requests,
            #btn-tb-success,
            #btn-tb-prev,
            #btn-tb-next,
            #btn-tb-close,
            #time_bucket_modal .btn-tb-failed,
            #time_bucket_modal .btn-tb-requests,
            #time_bucket_modal .btn-tb-success,
            #time_bucket_modal .btn-tb-prev,
            #time_bucket_modal .btn-tb-next,
            #time_bucket_modal .modal-footer button {
                border-radius: 10px !important;
            }
            /* API配置模态框按钮样式 */
            /* 保存按钮 - 蓝色 */
            #add_config_btn, #update_config_btn {
                background: #4285f4 !important;
                border-color: #4285f4 !important;
                color: white !important;
            }
            /* 取消按钮 - 灰色 */
            #cancel_add_btn, #cancel_edit_btn, #delete_cancel_btn {
                background: #f1f3f4 !important;
                border-color: #f1f3f4 !important;
                color: #3c4043 !important;
            }
            /* 删除确认按钮 - 红色 */
            #delete_confirm_btn {
                background: #ea4335 !important;
                border-color: #ea4335 !important;
                color: white !important;
            }
            /* 圆角化所有模态框按钮 */
            .api-modal .modal-footer button {
                border-radius: 10px !important;
            }
            
            /* 使用更具体的选择器来确保样式被应用 */
            div#add_config_btn, div#update_config_btn {
                background: #4285f4 !important;
                border-color: #4285f4 !important;
                color: white !important;
            }
            div#cancel_add_btn, div#cancel_edit_btn, div#delete_cancel_btn {
                background: #f1f3f4 !important;
                border-color: #f1f3f4 !important;
                color: #3c4043 !important;
            }
            div#delete_confirm_btn {
                background: #ea4335 !important;
                border-color: #ea4335 !important;
                color: white !important;
            }
            /* Hide Plotly modebar (top-right tool icons) globally */
            .js-plotly-plot .modebar, .js-plotly-plot .modebar-container { display: none !important; }
            /* Visually hide the hidden bridge input but keep it in DOM */
            #ts_clicked_bucket_input { display: none !important; }
            /* Center align the 4th column (进度) in dataframes to make progress visually aligned */
            table.dataframe thead th:nth-child(4),
            table.dataframe tbody td:nth-child(4) { text-align: center !important; }
            </style>
            """
        )

        # 全局：添加API的模态（放在根部，覆盖整个应用）
        with gr.Group(visible=False, elem_classes=["api-modal"]) as add_api_modal:
            gr.HTML('<div class="api-modal-backdrop"></div>')
            with gr.Group(elem_classes=["modal-content"]):
                gr.Markdown("#### 添加新的API配置")
                with gr.Row():
                    alias_input = gr.Textbox(label="别名", placeholder="例如: DeepSeek-V3")
                    model_input = gr.Textbox(label="模型名称", value="", placeholder="例如: DeepSeek-V3 或 gpt-4o-mini", elem_id="model_name_input")
                key_input = gr.Textbox(label="API Key", type="password")
                base_input = gr.Textbox(label="Base URL", value="https://openapi.coreshub.cn/v1")
                with gr.Row():
                    max_tokens_input = gr.Number(label="最大Token数", value=4096, minimum=1)
                    temperature_input = gr.Number(label="Temperature", value=0.7, minimum=0, maximum=2, step=0.1)
                    timeout_input = gr.Number(label="超时时间(秒)", value=60, minimum=1)
                gr.Markdown("##### 计费设置")
                with gr.Row():
                    currency_input = gr.Dropdown(label="币种", choices=["RMB", "USD"], value="RMB", scale=1)
                with gr.Row():
                    prompt_price_input = gr.Number(label="每1K输入Token单价", value=0.0, minimum=0.0, step=0.000001)
                    completion_price_input = gr.Number(label="每1K输出Token单价", value=0.0, minimum=0.0, step=0.000001)
                pricing_notes_input = gr.Textbox(label="价格备注", lines=2)
                add_is_active_checkbox = gr.Checkbox(label="是否激活", value=True)
                with gr.Row(elem_classes=["modal-footer"]):
                    add_config_btn = gr.Button("💾 保存", variant="primary", elem_id="add_config_btn")
                    cancel_add_btn = gr.Button("取消", elem_id="cancel_add_btn")

        # 全局：编辑API配置模态
        with gr.Group(visible=False, elem_classes=["api-modal"]) as edit_api_modal:
            gr.HTML('<div class="api-modal-backdrop"></div>')
            with gr.Group(elem_classes=["modal-content"]):
                gr.Markdown("#### 编辑API配置")
                edit_config_id = gr.State()
                with gr.Row():
                    edit_alias_input = gr.Textbox(label="别名")
                    edit_model_input = gr.Textbox(label="模型名称", elem_id="edit_model_name_input")
                edit_key_input = gr.Textbox(label="API Key", type="password")
                edit_base_input = gr.Textbox(label="Base URL")
                with gr.Row():
                    edit_max_tokens_input = gr.Number(label="最大Token数", minimum=1)
                    edit_temperature_input = gr.Number(label="Temperature", minimum=0, maximum=2, step=0.1)
                    edit_timeout_input = gr.Number(label="超时时间(秒)", minimum=1)
                gr.Markdown("##### 计费设置")
                with gr.Row():
                    edit_currency_input = gr.Dropdown(label="币种", choices=["RMB", "USD"]) 
                with gr.Row():
                    edit_prompt_price_input = gr.Number(label="每1K输入Token单价", minimum=0.0, step=0.000001)
                    edit_completion_price_input = gr.Number(label="每1K输出Token单价", minimum=0.0, step=0.000001)
                edit_pricing_notes_input = gr.Textbox(label="价格备注", lines=2)
                edit_is_active_checkbox = gr.Checkbox(label="是否激活")
                with gr.Row(elem_classes=["modal-footer"]):
                    update_config_btn = gr.Button("💾 保存", variant="primary", elem_id="update_config_btn")
                    cancel_edit_btn = gr.Button("取消", elem_id="cancel_edit_btn")

        # 全局：删除确认模态
        with gr.Group(visible=False, elem_classes=["api-modal"]) as delete_confirm_modal:
            gr.HTML('<div class="api-modal-backdrop"></div>')
            with gr.Group(elem_classes=["modal-content"]):
                gr.Markdown("#### 删除API配置")
                delete_confirm_text = gr.Markdown("确认删除该配置？此操作不可撤销。")
                with gr.Row(elem_classes=["modal-footer"]):
                    delete_confirm_btn = gr.Button("🗑️ 确认删除", variant="stop", elem_id="delete_confirm_btn")
                    delete_cancel_btn = gr.Button("取消", elem_id="delete_cancel_btn")

        # 全局：查看计费信息模态
        with gr.Group(visible=False, elem_classes=["api-modal"]) as billing_modal:
            gr.HTML('<div class="api-modal-backdrop"></div>')
            with gr.Group(elem_classes=["modal-content"]):
                gr.Markdown("#### 计费信息")
                billing_md = gr.Markdown(visible=True)
                with gr.Row(elem_classes=["modal-footer"]):
                    billing_close_btn = gr.Button("关闭")

        with gr.Tabs() as tabs:
            # --- Tab 1: 创建任务 ---
            with gr.TabItem("创建任务", id=0):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 上传任务文件")
                        file_input = gr.File(
                            label="JSON文件",
                            file_types=[".json"],
                            type="binary"
                        )
                        batch_name = gr.Textbox(label="任务名称", placeholder="输入批处理任务名称")
                        with gr.Row():
                            api_dropdown = gr.Dropdown(
                                label="选择API配置",
                                choices=UIComponents.get_api_aliases(),
                                value=None,
                                interactive=True
                            )
                        with gr.Row():
                            concurrency = gr.Number(
                                label="并发数",
                                value=5,
                                precision=0,
                                interactive=True
                            )
                            max_retries = gr.Number(
                                label="总尝试次数",
                                value=3,
                                precision=0,
                                interactive=True
                            )
                        create_btn = gr.Button("🚀 创建任务", variant="primary")
                    with gr.Column():
                        gr.Markdown("### 使用说明")
                        gr.Markdown("""
                        **支持的JSON文件格式：**
                        ```json
                        [
                            [{"role": "user", "content": "Hello"}],
                            [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "What is AI?"}]
                        ]
                        ```
                        **格式说明：**
                        - 文件是一个JSON数组，每个元素代表一个API请求
                        - 每个请求是一个消息数组，直接对应OpenAI API的messages参数
                        - 支持单轮对话（只有user消息）和多轮对话（system + user消息）
                        - 每条消息必须包含role和content字段
                        """)

            # --- Tab 2: 任务仪表盘 ---
            with gr.TabItem("任务仪表盘", id=1):
                with gr.Row():
                    refresh_btn = gr.Button("🔄 刷新", size="sm")
                    selected_job_index = gr.State()

                dashboard_df = gr.DataFrame(
                    value=UIComponents.refresh_dashboard(),
                    label="任务列表",
                    interactive=False,
                    wrap=True,
                    headers=['ID', '任务名称', '状态', '进度', '成功数', '失败数', '并发数', '创建时间']
                )

                with gr.Row():
                    delete_btn = gr.Button("🗑️ 删除作业", size="sm", variant="stop")
                    retry_failed_btn = gr.Button("🔁 重试失败请求", size="sm", variant="primary")
                    reset_job_btn = gr.Button("🔄 重置作业", size="sm")
                    pause_job_btn = gr.Button("⏸️ 暂停作业", size="sm")
                    resume_job_btn = gr.Button("▶️ 恢复作业", size="sm", variant="primary")
                    export_btn = gr.Button("📤 导出结果", size="sm", variant="primary")
                    # 用于浏览器下载导出文件的隐藏文件输出
                    export_file = gr.File(label="导出文件", visible=False)

                # 通用确认模态（兼容旧版Gradio：使用自定义 Group 模态）
                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_delete_modal") as confirm_delete_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认删除作业")
                        gr.Markdown("此操作将永久删除该作业及其请求和错误日志，确定要继续吗？")
                        with gr.Row():
                            confirm_delete_btn = gr.Button("确认删除", variant="stop")
                            cancel_delete_btn = gr.Button("取消")

                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_retry_failed_modal") as confirm_retry_failed_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认重试失败请求")
                        gr.Markdown("将对该作业下的所有失败请求执行重试，确定继续吗？")
                        with gr.Row():
                            confirm_retry_failed_btn = gr.Button("确认重试", variant="primary")
                            cancel_retry_failed_btn = gr.Button("取消")

                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_reset_job_modal") as confirm_reset_job_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认重置作业")
                        gr.Markdown("将把该作业重置为未处理状态，清空进度并可重新开始，确定继续吗？")
                        with gr.Row():
                            confirm_reset_job_btn = gr.Button("确认重置")
                            cancel_reset_job_btn = gr.Button("取消")

                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_pause_job_modal") as confirm_pause_job_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认暂停作业")
                        gr.Markdown("将暂停该作业的执行，确定继续吗？")
                        with gr.Row():
                            confirm_pause_job_btn = gr.Button("确认暂停")
                            cancel_pause_job_btn = gr.Button("取消")

                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_resume_job_modal") as confirm_resume_job_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认恢复作业")
                        gr.Markdown("将恢复该作业的执行，确定继续吗？")
                        with gr.Row():
                            confirm_resume_job_btn = gr.Button("确认恢复", variant="primary")
                            cancel_resume_job_btn = gr.Button("取消")

                with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_export_modal") as confirm_export_modal:
                    gr.HTML('<div class="api-modal-backdrop"></div>')
                    with gr.Group(elem_classes=["modal-content"]):
                        gr.Markdown("### 确认导出结果")
                        gr.Markdown("将导出该作业的结果文件，确定继续吗？")
                        with gr.Row():
                            confirm_export_btn = gr.Button("确认导出", variant="primary")
                            cancel_export_btn = gr.Button("取消")

                gr.Markdown("### 任务详情")
                gr.Markdown("**提示：** 点击上方表格中的任务行查看详细信息。")

                with gr.Tabs():
                    with gr.TabItem("请求详情"):
                        requests_df = gr.DataFrame(
                            label="请求列表",
                            interactive=False,
                            wrap=True,
                            headers=['ID', '请求索引', '状态', '重试次数', '输入Token', '输出Token', '总Token','开始时间', '结束时间']
                        )
                        # 请求表格分页控件（每页20条）
                        req_table_current_page = gr.State(value=1)
                        # 第一行：每页数量 + 跳转页码
                        with gr.Row():
                            req_table_page_size = gr.Dropdown(label="每页数量", choices=[20,50,100], value=20, scale=1)
                            req_table_jump_page = gr.Number(label="跳转页码", precision=0, value=1, minimum=1)
                        # 信息行：分页信息展示
                        with gr.Row():
                            req_table_page_info_md = gr.Markdown()
                        # 第二行：上一页 / 下一页 / 跳转按钮
                        with gr.Row():
                            req_table_prev_btn = gr.Button("⬅️ 上一页", size="sm", variant="primary")
                            req_table_next_btn = gr.Button("下一页 ➡️", size="sm", variant="primary")
                            req_table_jump_btn = gr.Button("跳转", size="sm")
                        with gr.Row():
                            selected_request_index = gr.State()
                            retry_request_btn = gr.Button("🔁 重试选中请求", size="sm", variant="primary")

                        with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="confirm_retry_request_modal") as confirm_retry_request_modal:
                            gr.HTML('<div class="api-modal-backdrop"></div>')
                            with gr.Group(elem_classes=["modal-content"]):
                                gr.Markdown("### 确认重试选中请求")
                                gr.Markdown("将重试上方列表中选中的一条请求，确定继续吗？")
                                with gr.Row():
                                    confirm_retry_request_btn = gr.Button("确认重试", variant="primary")
                                    cancel_retry_request_btn = gr.Button("取消")
                        # 单条请求内容查看
                        with gr.Accordion("选中请求内容", open=True):
                            req_detail_md = gr.Markdown()
                            with gr.Row():
                                req_messages_json = gr.JSON(label="Messages")
                                req_response_code = gr.Code(label="Response", language="json")

                    with gr.TabItem("错误日志"):
                        errors_df = gr.DataFrame(
                            label="错误列表",
                            interactive=False,
                            wrap=True,
                            headers=['ID', '请求ID', '错误类型', '错误信息', '创建时间']
                        )
                        # 错误日志表格分页控件
                        err_table_current_page = gr.State(value=1)
                        # 第一行：每页数量 + 跳转页码
                        with gr.Row():
                            err_table_page_size = gr.Dropdown(label="每页数量", choices=[20,50,100], value=20, scale=1)
                            err_table_jump_page = gr.Number(label="跳转页码", precision=0, value=1, minimum=1)
                        # 信息行
                        with gr.Row():
                            err_table_page_info_md = gr.Markdown()
                        # 第二行：上一页 / 下一页 / 跳转按钮（按钮配色与请求表一致）
                        with gr.Row():
                            err_table_prev_btn = gr.Button("⬅️ 上一页", size="sm", variant="primary")
                            err_table_next_btn = gr.Button("下一页 ➡️", size="sm", variant="primary")
                            err_table_jump_btn = gr.Button("跳转", size="sm")

                    with gr.TabItem("性能统计"):
                        performance_df = gr.DataFrame(
                            label="性能指标",
                            interactive=False,
                            wrap=True,
                            headers=['平均响应时间(秒)', '总处理时间(秒)', '每秒请求数', '总成本']
                        )
                        with gr.Row():
                            ts_interval = gr.Dropdown(
                                label="时间间隔",
                                choices=["10ms", "100ms", "1s", "10s", "1min", "5min"],
                                value="1s",
                                scale=1,
                                interactive=True
                            )
                        # 新增：时间序列折线图（Plotly，可缩放）
                        performance_ts_plot = gr.Plot(label="请求/成功/失败", elem_id="ts_plot")
                        # 隐藏输入：承接图表点击的时间桶（保持可见便于调试/确认）
                        ts_clicked_bucket = gr.Textbox(label="ts_clicked_bucket", visible=True, elem_id="ts_clicked_bucket_input")

                    # 新增：API 详情 Tab
                    with gr.TabItem("API 详情"):
                        api_detail_df = gr.DataFrame(
                            label="API 配置详情",
                            interactive=False,
                            wrap=True,
                            headers=['ID', '别名', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活',
                                     '创建时间', '更新时间']
                        )

                    # 新增：请求内容分页查看（每页2条）
                    with gr.TabItem("请求内容"):
                        # 轻量样式优化
                        gr.HTML(
                            """
                            <style>
                              .request-cards { gap: 12px; }
                              .request-card .label-wrap { display:none; }
                              .request-card pre, .request-card code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12.5px; }
                              .request-card .svelte-jsoneditor-tree { max-height: 340px; overflow: auto; }
                              .request-card .wrap.svelte-1ipelgc textarea { max-height: 340px; overflow: auto; }
                              /* 让 Code 组件自动换行并限制高度 */
                              .request-card .cm-editor { max-height: 340px; border-radius: 6px; }
                              .request-card .cm-scroller { overflow: auto; }
                              .request-card .cm-content { white-space: pre-wrap; word-break: break-word; }
                            </style>
                            """
                        )
                        current_page = gr.State(value=1)
                        page_info_md = gr.Markdown(visible=True)
                        with gr.Row():
                            prev_page_btn = gr.Button("⬅️ 上一页", size="sm", variant="primary")
                            next_page_btn = gr.Button("下一页 ➡️", size="sm", variant="primary")
                        with gr.Column(elem_classes=["request-cards"]):
                            with gr.Accordion("第1条", open=True, elem_classes=["request-card"]):
                                md1_summary = gr.Markdown()
                                with gr.Row():
                                    messages1 = gr.JSON(label="Messages #1")
                                    response1 = gr.Code(label="Response #1", language="json")
                            with gr.Accordion("第2条", open=True, elem_classes=["request-card"]):
                                md2_summary = gr.Markdown()
                                with gr.Row():
                                    messages2 = gr.JSON(label="Messages #2")
                                    response2 = gr.Code(label="Response #2", language="json")

            # --- Tab 3: API配置管理 ---
            with gr.TabItem("API配置", id=2):
                # 调整布局：操作按钮横向一行，操作区与API列表上下排布
                with gr.Column():
                    gr.Markdown("### 操作")
                    with gr.Row():
                        add_api_open_btn = gr.Button("➕ 添加API", variant="primary")
                        edit_open_btn = gr.Button("✏️ 编辑配置")
                        delete_open_btn = gr.Button("🗑️ 删除配置", variant="stop")
                        view_billing_btn = gr.Button("💰 查看计费")
                    gr.Markdown("### 现有API配置")
                    api_configs_df = gr.DataFrame(
                        value=UIComponents.refresh_api_configs(),
                        interactive=False,
                        wrap=True,
                        headers=['ID', '别名', 'api_key', 'API地址', '模型名称', '最大Token', '温度', '超时(秒)', '是否激活', '创建时间', '更新时间']
                    )
                    # 隐藏输入：用于复制api_key
                    copy_api_key_holder = gr.Textbox(visible=False)

        # --- 时间桶详情模态 ---
        with gr.Group(visible=False, elem_classes=["api-modal"], elem_id="time_bucket_modal") as time_bucket_modal:
            gr.HTML('<div class="api-modal-backdrop"></div>')
            with gr.Group(elem_classes=["modal-content"]) as tb_modal_content:
                tb_title_md = gr.Markdown("#### 时间点详情")
                with gr.Row():
                    cat_failed_state = gr.State(value="failed")
                    cat_requests_state = gr.State(value="requests")
                    cat_success_state = gr.State(value="success")
                    btn_tb_failed = gr.Button("失败", variant="stop", elem_classes=["btn-tb-failed"], 
                                            elem_id="btn-tb-failed")
                    btn_tb_requests = gr.Button("请求", variant="secondary", elem_classes=["btn-tb-requests"], 
                                              elem_id="btn-tb-requests")
                    btn_tb_success = gr.Button("成功", variant="primary", elem_classes=["btn-tb-success"], 
                                             elem_id="btn-tb-success")
                tb_count_md = gr.Markdown()
                # 记录当前时间桶下的条目与索引
                tb_items_state = gr.State(value=[])
                tb_index_state = gr.State(value=0)
                tb_category_state = gr.State(value="failed")
                tb_bucket_state = gr.State(value="")
                with gr.Row():
                    tb_messages_json = gr.JSON(label="Messages", scale=1)
                    tb_response_code = gr.Code(label="Response", language="json", lines=30, scale=1)
                with gr.Row(elem_classes=["modal-footer"]):
                    btn_tb_prev = gr.Button("上一条", variant="secondary", elem_classes=["btn-tb-prev"], 
                                          elem_id="btn-tb-prev")
                    btn_tb_next = gr.Button("下一条", variant="secondary", elem_classes=["btn-tb-next"], 
                                          elem_id="btn-tb-next")
                    btn_tb_close = gr.Button("关闭")

        # === Tab 切换时自动刷新数据 ===
        tabs.select(
            fn=UIEventHandlers.on_tab_change,
            inputs=[],
            outputs=[dashboard_df, api_configs_df, api_dropdown]
        )
        
        # === 其他事件处理 ===
        create_btn.click(
            fn=UIEventHandlers.create_job_and_show_status,
            inputs=[file_input, batch_name, api_dropdown, concurrency, max_retries],
            outputs=[tabs, dashboard_df]
        )
        refresh_btn.click(fn=UIComponents.refresh_dashboard, outputs=[dashboard_df])
        dashboard_df.select(
            fn=UIEventHandlers.show_job_details_and_update_selection,
            inputs=[dashboard_df],
            outputs=[requests_df, errors_df, performance_df, performance_ts_plot, api_detail_df, selected_job_index]
        )
        # 选择作业时，加载“请求详情”表格的第一页（20条）
        dashboard_df.select(
            fn=UIEventHandlers.load_requests_table_page,
            inputs=[dashboard_df, selected_job_index, req_table_current_page, req_table_page_size],
            outputs=[requests_df, req_table_page_info_md, req_table_current_page]
        )
        # 选择作业时，加载“错误日志”表格的第一页（20条）
        dashboard_df.select(
            fn=UIEventHandlers.load_errors_table_page,
            inputs=[dashboard_df, selected_job_index, err_table_current_page, err_table_page_size],
            outputs=[errors_df, err_table_page_info_md, err_table_current_page]
        )
        # 切换作业时，自动加载该作业的第一条请求详情
        dashboard_df.select(
            fn=UIEventHandlers.load_first_request_detail,
            inputs=[dashboard_df],
            outputs=[req_detail_md, req_messages_json, req_response_code, selected_request_index]
        )
        # 选择作业时，同步加载“请求内容”的第一页
        dashboard_df.select(
            fn=UIEventHandlers.load_request_page,
            inputs=[dashboard_df, selected_job_index, current_page],
            outputs=[page_info_md, md1_summary, messages1, response1, md2_summary, messages2, response2, current_page]
        )
        ts_interval.change(
            fn=UIEventHandlers.refresh_time_series_only,
            inputs=[dashboard_df, selected_job_index, ts_interval],
            outputs=[performance_ts_plot]
        )
        # 在切换作业时（更新了图表输出），也自动绑定一次
        dashboard_df.select(
            fn=UIEventHandlers.show_job_details_and_update_selection,
            inputs=[dashboard_df],
            outputs=[requests_df, errors_df, performance_df, performance_ts_plot, api_detail_df, selected_job_index]
        )
        # 页面加载时绑定一次 Plotly 点击（不触发后端，仅前端写入隐藏输入）
        app.load(
            fn=None,
            inputs=None,
            outputs=None,
            js="""
            () => {
              const appRoot = (() => { try { return (window.gradioApp && window.gradioApp()) || document; } catch(e){ return document; }})();
              
              // 设置按钮样式
              const setButtonStyles = () => {
                // 保存按钮 - 蓝色
                const saveButtons = appRoot.querySelectorAll('#add_config_btn, #update_config_btn');
                saveButtons.forEach(btn => {
                  const button = btn.querySelector('button') || btn;
                  button.style.background = '#4285f4';
                  button.style.borderColor = '#4285f4';
                  button.style.color = 'white';
                });
                
                // 取消按钮 - 灰色
                const cancelButtons = appRoot.querySelectorAll('#cancel_add_btn, #cancel_edit_btn, #delete_cancel_btn');
                cancelButtons.forEach(btn => {
                  const button = btn.querySelector('button') || btn;
                  button.style.background = '#f1f3f4';
                  button.style.borderColor = '#f1f3f4';
                  button.style.color = '#3c4043';
                });
                
                // 删除确认按钮 - 红色
                const deleteButtons = appRoot.querySelectorAll('#delete_confirm_btn');
                deleteButtons.forEach(btn => {
                  const button = btn.querySelector('button') || btn;
                  button.style.background = '#ea4335';
                  button.style.borderColor = '#ea4335';
                  button.style.color = 'white';
                });
                
                // 圆角所有模态框按钮
                const allButtons = appRoot.querySelectorAll('.api-modal .modal-footer button');
                allButtons.forEach(btn => {
                  btn.style.borderRadius = '10px';
                });
              };
              
              // 绑定Plotly点击事件
              const bind = () => {
                const host = appRoot.querySelector('#ts_plot .js-plotly-plot, #ts_plot .plotly-graph-div');
                if(!host || host.__bound_click){ return; }
                host.__bound_click = true;
                host.on('plotly_click', (e) => {
                  try{
                    const pt = (e && e.points && e.points[0]) || {};
                    const vx = pt.x;
                    const wrap = appRoot.querySelector('#ts_clicked_bucket_input');
                    if(wrap){
                      const input = wrap.querySelector('input, textarea');
                      if(input){
                        input.value = (typeof vx === 'string') ? vx : (vx ? vx.toString() : '');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                      }
                    }
                  }catch(err){ console.warn('plot click handler error', err); }
                });
              };
              
              // 应用按钮样式
              setButtonStyles();
              // 定期检查并重新应用样式（应对动态加载的元素）
              setInterval(setButtonStyles, 500);
              
              const iv = setInterval(bind, 400);
              setTimeout(bind, 200);
            }
            """
        )
        # 点击图表（隐藏输入变化）时，打开模态并加载默认（失败）类别
        ts_clicked_bucket.change(
            fn=UIEventHandlers.open_time_bucket_modal,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket],
            outputs=[time_bucket_modal, tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_items_state, tb_index_state, tb_category_state, tb_bucket_state]
        )
        # 模态内切换类别
        btn_tb_failed.click(
            fn=UIEventHandlers.load_time_bucket_by_category,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket, cat_failed_state],
            outputs=[tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_items_state, tb_index_state, tb_category_state]
        )
        btn_tb_requests.click(
            fn=UIEventHandlers.load_time_bucket_by_category,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket, cat_requests_state],
            outputs=[tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_items_state, tb_index_state, tb_category_state]
        )
        btn_tb_success.click(
            fn=UIEventHandlers.load_time_bucket_by_category,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket, cat_success_state],
            outputs=[tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_items_state, tb_index_state, tb_category_state]
        )
        # 上一条 / 下一条
        btn_tb_prev.click(
            fn=UIEventHandlers.change_time_bucket_index,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket, tb_items_state, tb_index_state, tb_category_state, tb_bucket_state, gr.State(value=-1)],
            outputs=[tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_index_state]
        )
        btn_tb_next.click(
            fn=UIEventHandlers.change_time_bucket_index,
            inputs=[dashboard_df, selected_job_index, ts_interval, ts_clicked_bucket, tb_items_state, tb_index_state, tb_category_state, tb_bucket_state, gr.State(value=1)],
            outputs=[tb_title_md, tb_count_md, tb_messages_json, tb_response_code, tb_index_state]
        )
        # 关闭模态
        btn_tb_close.click(lambda: gr.update(visible=False), outputs=[time_bucket_modal])
        # 打开确认模态
        delete_btn.click(lambda: gr.update(visible=True), outputs=[confirm_delete_modal])
        retry_failed_btn.click(lambda: gr.update(visible=True), outputs=[confirm_retry_failed_modal])
        reset_job_btn.click(lambda: gr.update(visible=True), outputs=[confirm_reset_job_modal])
        pause_job_btn.click(lambda: gr.update(visible=True), outputs=[confirm_pause_job_modal])
        resume_job_btn.click(lambda: gr.update(visible=True), outputs=[confirm_resume_job_modal])
        export_btn.click(lambda: gr.update(visible=True), outputs=[confirm_export_modal])

        # 取消关闭模态
        cancel_delete_btn.click(lambda: gr.update(visible=False), outputs=[confirm_delete_modal])
        cancel_retry_failed_btn.click(lambda: gr.update(visible=False), outputs=[confirm_retry_failed_modal])
        cancel_reset_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_reset_job_modal])
        cancel_pause_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_pause_job_modal])
        cancel_resume_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_resume_job_modal])
        cancel_export_btn.click(lambda: gr.update(visible=False), outputs=[confirm_export_modal])

        # 确认执行 + 关闭模态
        confirm_delete_btn.click(
            fn=UIEventHandlers.delete_job,
            inputs=[dashboard_df, selected_job_index],
            outputs=[dashboard_df]
        )
        confirm_delete_btn.click(lambda: gr.update(visible=False), outputs=[confirm_delete_modal])

        confirm_retry_failed_btn.click(
            fn=UIEventHandlers.retry_failed_requests,
            inputs=[dashboard_df, selected_job_index],
            outputs=[dashboard_df]
        )
        confirm_retry_failed_btn.click(lambda: gr.update(visible=False), outputs=[confirm_retry_failed_modal])

        confirm_reset_job_btn.click(
            fn=UIEventHandlers.reset_job,
            inputs=[dashboard_df, selected_job_index],
            outputs=[dashboard_df]
        )
        confirm_reset_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_reset_job_modal])

        confirm_pause_job_btn.click(
            fn=UIEventHandlers.pause_job,
            inputs=[dashboard_df, selected_job_index],
            outputs=[dashboard_df]
        )
        confirm_pause_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_pause_job_modal])

        confirm_resume_job_btn.click(
            fn=UIEventHandlers.resume_job,
            inputs=[dashboard_df, selected_job_index],
            outputs=[dashboard_df]
        )
        confirm_resume_job_btn.click(lambda: gr.update(visible=False), outputs=[confirm_resume_job_modal])

        confirm_export_btn.click(
            fn=UIEventHandlers.export_job_results,
            inputs=[dashboard_df, selected_job_index],
            outputs=[export_file]
        )
        confirm_export_btn.click(lambda: gr.update(visible=False), outputs=[confirm_export_modal])
        # 添加请求表格的选择事件处理（记录索引 + 展示详情）
        requests_df.select(
            fn=UIEventHandlers.show_request_selection,
            inputs=[],
            outputs=[selected_request_index]
        )
        requests_df.select(
            fn=UIEventHandlers.load_request_detail_by_evt,
            inputs=[requests_df],
            outputs=[req_detail_md, req_messages_json, req_response_code]
        )
        # 重试单个请求 —— 弹窗确认
        retry_request_btn.click(lambda: gr.update(visible=True), outputs=[confirm_retry_request_modal])
        cancel_retry_request_btn.click(lambda: gr.update(visible=False), outputs=[confirm_retry_request_modal])
        confirm_retry_request_btn.click(
            fn=UIEventHandlers.retry_request,
            inputs=[requests_df, selected_request_index],
            outputs=[dashboard_df]
        )
        confirm_retry_request_btn.click(lambda: gr.update(visible=False), outputs=[confirm_retry_request_modal])
        # 请求表格翻页事件
        req_table_prev_btn.click(
            fn=UIEventHandlers.requests_table_prev,
            inputs=[dashboard_df, selected_job_index, req_table_current_page, req_table_page_size],
            outputs=[requests_df, req_table_page_info_md, req_table_current_page]
        )
        req_table_next_btn.click(
            fn=UIEventHandlers.requests_table_next,
            inputs=[dashboard_df, selected_job_index, req_table_current_page, req_table_page_size],
            outputs=[requests_df, req_table_page_info_md, req_table_current_page]
        )
        # 修改每页数量
        req_table_page_size.change(
            fn=UIEventHandlers.requests_table_change_page_size,
            inputs=[dashboard_df, selected_job_index, req_table_page_size],
            outputs=[requests_df, req_table_page_info_md, req_table_current_page]
        )
        # 跳转到指定页
        req_table_jump_btn.click(
            fn=UIEventHandlers.requests_table_jump,
            inputs=[dashboard_df, selected_job_index, req_table_jump_page, req_table_page_size],
            outputs=[requests_df, req_table_page_info_md, req_table_current_page]
        )
        # 错误日志表格翻页事件
        err_table_prev_btn.click(
            fn=UIEventHandlers.errors_table_prev,
            inputs=[dashboard_df, selected_job_index, err_table_current_page, err_table_page_size],
            outputs=[errors_df, err_table_page_info_md, err_table_current_page]
        )
        err_table_next_btn.click(
            fn=UIEventHandlers.errors_table_next,
            inputs=[dashboard_df, selected_job_index, err_table_current_page, err_table_page_size],
            outputs=[errors_df, err_table_page_info_md, err_table_current_page]
        )
        err_table_page_size.change(
            fn=UIEventHandlers.errors_table_change_page_size,
            inputs=[dashboard_df, selected_job_index, err_table_page_size],
            outputs=[errors_df, err_table_page_info_md, err_table_current_page]
        )
        err_table_jump_btn.click(
            fn=UIEventHandlers.errors_table_jump,
            inputs=[dashboard_df, selected_job_index, err_table_jump_page, err_table_page_size],
            outputs=[errors_df, err_table_page_info_md, err_table_current_page]
        )
        # 翻页按钮事件
        prev_page_btn.click(
            fn=UIEventHandlers.request_page_prev,
            inputs=[dashboard_df, selected_job_index, current_page],
            outputs=[page_info_md, md1_summary, messages1, response1, md2_summary, messages2, response2, current_page]
        )
        next_page_btn.click(
            fn=UIEventHandlers.request_page_next,
            inputs=[dashboard_df, selected_job_index, current_page],
            outputs=[page_info_md, md1_summary, messages1, response1, md2_summary, messages2, response2, current_page]
        )
        add_config_btn.click(
            fn=UIEventHandlers.add_api_config_and_refresh,
            inputs=[alias_input, key_input, base_input, model_input, max_tokens_input, temperature_input,
                    timeout_input, currency_input, prompt_price_input, completion_price_input, pricing_notes_input,
                    add_is_active_checkbox],
            outputs=[api_configs_df]
        )
        # 兼容旧版Gradio：再次绑定点击以关闭模态
        add_config_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[add_api_modal]
        )
        # 打开/关闭模态的事件
        add_api_open_btn.click(
            fn=lambda: gr.update(visible=True),
            inputs=None,
            outputs=[add_api_modal],
            js="""
            () => {
              const app = (()=>{ try { return (window.gradioApp && window.gradioApp()) || document; } catch(e){ return document; } })();
              setTimeout(()=>{
                const host = app.querySelector('#model_name_input');
                const input = host && host.querySelector('input, textarea');
                if(input){
                  try{
                    host.style.display = 'block'; host.style.visibility = 'visible';
                    input.scrollIntoView({behavior:'smooth', block:'center'});
                    input.style.outline = '2px solid #f00';
                    input.focus();
                    setTimeout(()=>{ input.style.outline=''; }, 1600);
                  }catch(_){}
                }
              }, 50);
            }
            """
        )
        cancel_add_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[add_api_modal]
        )
        api_configs_df.select(
            fn=UIEventHandlers.load_api_config_for_edit,
            inputs=[api_configs_df],
            outputs=[edit_config_id, edit_alias_input, edit_key_input, edit_base_input, edit_model_input, 
                     edit_max_tokens_input, edit_temperature_input, edit_timeout_input,
                     edit_currency_input, edit_prompt_price_input, edit_completion_price_input,
                     edit_pricing_notes_input, edit_is_active_checkbox]
        )
        update_config_btn.click(
            fn=UIEventHandlers.update_api_config_and_refresh,
            inputs=[edit_config_id, edit_alias_input, edit_key_input, edit_base_input, edit_model_input,
                    edit_max_tokens_input, edit_temperature_input, edit_timeout_input,
                    edit_currency_input, edit_prompt_price_input, edit_completion_price_input,
                    edit_pricing_notes_input, edit_is_active_checkbox],
            outputs=[api_configs_df]
        )
        # 更新后关闭编辑模态
        update_config_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[edit_api_modal]
        )
        # 当聚焦到 API 下拉框时，自动刷新可选项
        api_dropdown.focus(
            fn=lambda: gr.Dropdown(choices=UIComponents.get_api_aliases()),
            inputs=None,
            outputs=[api_dropdown]
        )

        # 打开/关闭编辑模态
        edit_open_btn.click(
            fn=lambda: gr.update(visible=True),
            inputs=None,
            outputs=[edit_api_modal],
            js="""
            () => {
              const app = (()=>{ try { return (window.gradioApp && window.gradioApp()) || document; } catch(e){ return document; } })();
              setTimeout(()=>{
                const host = app.querySelector('#edit_model_name_input');
                const input = host && host.querySelector('input, textarea');
                if(input){
                  try{
                    host.style.display = 'block'; host.style.visibility = 'visible';
                    input.scrollIntoView({behavior:'smooth', block:'center'});
                    input.style.outline = '2px solid #f00';
                    input.focus();
                    setTimeout(()=>{ input.style.outline=''; }, 1600);
                  }catch(_){}
                }
              }, 50);
            }
            """
        )
        cancel_edit_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[edit_api_modal]
        )

        # 打开删除确认模态并填充提示文案
        def _del_prompt_text(alias):
            return f"确认删除配置：**{alias or ''}**？此操作不可撤销。"
        delete_open_btn.click(
            fn=lambda alias: (_del_prompt_text(alias), gr.update(visible=True)),
            inputs=[edit_alias_input],
            outputs=[delete_confirm_text, delete_confirm_modal]
        )
        delete_cancel_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[delete_confirm_modal]
        )
        delete_confirm_btn.click(
            fn=UIEventHandlers.delete_api_config_and_refresh,
            inputs=[edit_config_id],
            outputs=[api_configs_df]
        )
        delete_confirm_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[delete_confirm_modal]
        )

        # 查看计费信息
        view_billing_btn.click(
            fn=UIEventHandlers.open_billing_modal,
            inputs=[edit_config_id],
            outputs=[billing_modal, billing_md]
        )
        billing_close_btn.click(
            fn=lambda: gr.update(visible=False),
            inputs=None,
            outputs=[billing_modal]
        )

        # 点击DataFrame中的api_key单元格 -> 获取真实key到隐藏文本框
        api_configs_df.select(
            fn=UIEventHandlers.copy_api_key_on_click,
            inputs=[api_configs_df],
            outputs=[copy_api_key_holder]
        )
        # 隐藏文本框变更时，前端JS将内容复制到剪贴板并给出提示
        copy_api_key_holder.change(
            fn=None,
            inputs=[copy_api_key_holder],
            outputs=[],
            js="""
            (v)=>{
              if(!v) return [];
              navigator.clipboard?.writeText(v);
              // create toast container if not exists
              let toast = document.getElementById('gr-toast');
              if(!toast){
                toast = document.createElement('div');
                toast.id = 'gr-toast';
                toast.style.cssText = `
                  position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%);
                  background: rgba(0,0,0,0.75); color: #fff; padding: 8px 14px; border-radius: 8px;
                  font-size: 14px; z-index: 9999; opacity: 0; transition: opacity .2s ease;
                  pointer-events: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                `;
                document.body.appendChild(toast);
              }
              toast.textContent = '已复制 API Key 到剪贴板';
              toast.style.opacity = '1';
              clearTimeout(window.__gr_toast_timer);
              window.__gr_toast_timer = setTimeout(()=>{ toast.style.opacity = '0'; }, 1600);
              return [];
            }
            """
        )

    return app