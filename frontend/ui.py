"""
用户界面模块，负责创建和管理Gradio UI。
"""

import asyncio
import nest_asyncio

from frontend.layout import create_ui_layout
from core.logger import get_logger

# 允许嵌套事件循环
nest_asyncio.apply()

# 获取日志记录器
logger = get_logger(__name__)


def create_ui():
    """
    创建并返回Gradio UI应用。
    
    Returns:
        gr.Blocks: Gradio UI应用
    """
    logger.info("正在创建UI应用...")
    try:
        app = create_ui_layout()
        logger.info("UI应用创建成功")
        return app
    except Exception as e:
        logger.error(f"创建UI应用时出错: {e}", exc_info=True)
        raise