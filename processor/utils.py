"""
处理器工具模块，包含通用的辅助函数，减少重复代码。
"""

import asyncio
from typing import Optional, List, Any, Dict
from datetime import datetime

import curd.batch_job_curd
from core.logger import get_logger
import settings

# 获取日志记录器
logger = get_logger(__name__)


class JobValidator:
    """作业验证器，统一处理作业相关的检查逻辑"""
    
    @staticmethod
    async def check_job_exists(job_id: int) -> bool:
        """检查作业是否存在"""
        try:
            job_details = await curd.batch_job_curd.get_job_details(job_id)
            return job_details is not None
        except Exception:
            return False
    
    @staticmethod
    async def get_job_details_safe(job_id: int) -> Optional[Dict[str, Any]]:
        """安全获取作业详情，异常时返回None"""
        try:
            return await curd.batch_job_curd.get_job_details(job_id)
        except Exception:
            return None
    
    @staticmethod
    async def wait_if_job_paused(job_id: int, check_interval: float = None):
        """如果作业被暂停，则等待直到恢复"""
        if check_interval is None:
            check_interval = settings.JOB_PAUSE_CHECK_INTERVAL
        try:
            while True:
                job_details = await JobValidator.get_job_details_safe(job_id)
                if not job_details:
                    return
                status = job_details.get('status') if isinstance(job_details, dict) else None
                if status != 'paused':
                    return
                await asyncio.sleep(check_interval)
        except Exception:
            # 保守处理，任何异常都不阻塞请求执行
            return


class TaskManager:
    """任务管理器，统一处理异步任务的创建、取消和清理"""
    
    @staticmethod
    async def cancel_task_safely(task: asyncio.Task, task_name: str = "未知任务"):
        """安全取消任务"""
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"{task_name} 已被安全取消")
            except Exception as e:
                logger.warning(f"{task_name} 取消时发生异常: {e}")
    
    @staticmethod
    async def cancel_tasks_safely(tasks: List[asyncio.Task], task_group_name: str = "任务组"):
        """批量安全取消任务"""
        if not tasks:
            return
        
        logger.debug(f"正在取消 {task_group_name} 中的 {len(tasks)} 个任务")
        cancel_operations = [
            TaskManager.cancel_task_safely(task, f"{task_group_name}任务{i}")
            for i, task in enumerate(tasks)
        ]
        await asyncio.gather(*cancel_operations, return_exceptions=True)
        logger.debug(f"{task_group_name} 中的所有任务已安全取消")


class ErrorHandler:
    """错误处理器，统一异常处理和日志记录模式"""
    
    @staticmethod
    def log_and_return_default(operation_name: str, exception: Exception, 
                               default_value: Any = None, 
                               job_id: Optional[int] = None) -> Any:
        """记录异常并返回默认值"""
        job_info = f" (作业 {job_id})" if job_id else ""
        logger.error(f"{operation_name}{job_info} 失败: {exception}", exc_info=True)
        return default_value
    
    @staticmethod
    async def log_and_continue(operation_name: str, coro_func, 
                               job_id: Optional[int] = None, 
                               suppress_exceptions: bool = True) -> Any:
        """执行异步操作，记录异常并继续"""
        try:
            return await coro_func()
        except Exception as e:
            if suppress_exceptions:
                return ErrorHandler.log_and_return_default(operation_name, e, job_id=job_id)
            else:
                raise


class TimeUtils:
    """时间工具类"""
    
    @staticmethod
    def get_current_time_iso() -> str:
        """获取当前时间的ISO格式字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
