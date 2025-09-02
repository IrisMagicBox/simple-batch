# main.py

import asyncio
import argparse
from contextlib import asynccontextmanager

from database import initialize_database
from processor import scheduler
from frontend.ui import create_ui
from core.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan():
    """应用生命周期管理。"""
    # 启动阶段
    
    # 1. 初始化数据库
    await initialize_database()
    logger.info("数据库初始化完成")
    
    # 2. 启动调度器
    scheduler_task = asyncio.create_task(scheduler())
    logger.info("调度器已启动")
    
    try:
        yield  # 应用运行期间
    finally:
        # 清理阶段
        logger.info("正在关闭应用...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("调度器已停止")


def run_ui(host="127.0.0.1", port=7861):
    """启动UI服务器。
    
    Args:
        host (str): 服务器绑定的主机地址
        port (int): 服务器监听的端口号
    """
    logger.info(f"正在启动UI服务器在 {host}:{port}...")
    web_ui = create_ui()
    web_ui.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True,
        quiet=False
    )


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description='启动批处理服务')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                      help='服务器绑定的主机地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=7861,
                      help='服务器监听的端口号 (默认: 7861)')
    return parser.parse_args()


async def main():
    """主函数，管理应用生命周期并启动UI。"""
    args = parse_args()
    
    async with app_lifespan():
        # 在异步上下文中启动UI（阻塞运行）
        await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: run_ui(host=args.host, port=args.port)
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("应用程序被用户中断")
    except Exception as e:
        logger.error(f"应用程序运行失败: {e}", exc_info=True)
        raise
