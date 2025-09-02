"""
作业处理器模块，负责处理单个批处理作业。
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any

from models import BatchJob, APIInfo
import curd.api_info_curd
import curd.batch_job_curd
import curd.batch_requests_curd
import curd.error_logs_curd
from service import performance_info_service
from processor.request_cache import RequestCache
from processor.request_executor import execute_request
from processor.utils import JobValidator, TaskManager, ErrorHandler, TimeUtils
import database as db
from const import JobStatus, RequestStatus, ErrorType
from core.logger import get_logger
import settings

# 获取日志记录器
logger = get_logger(__name__)


async def _create_background_tasks(job_id: int, request_cache: RequestCache, job_tasks: List[asyncio.Task]) -> List[asyncio.Task]:
    """创建后台任务组，统一管理定期任务"""
    
    async def cancel_on_job_deleted():
        """监听作业删除事件并取消任务"""
        try:
            while True:
                await asyncio.sleep(settings.JOB_DELETION_CHECK_INTERVAL)
                if not await JobValidator.check_job_exists(job_id):
                    logger.info(f"检测到作业 {job_id} 已被删除，正在取消所有相关任务...")
                    # 取消所有与该作业相关的任务
                    for task in job_tasks:
                        if not task.done():
                            task.cancel()
                    logger.info(f"作业 {job_id} 的相关任务取消指令已发送。")
                    break
        except asyncio.CancelledError:
            pass

    async def flush_cache_periodically():
        """定期刷新缓存"""
        try:
            while True:
                await asyncio.sleep(request_cache.flush_interval)
                await request_cache.flush_updates()
        except asyncio.CancelledError:
            pass
    
    async def update_performance_periodically():
        """定期更新性能统计"""
        try:
            while True:
                await asyncio.sleep(settings.PERFORMANCE_UPDATE_INTERVAL)
                if not await JobValidator.check_job_exists(job_id):
                    logger.info(f"作业 {job_id} 已被删除，停止性能统计定期更新任务。")
                    break
                await ErrorHandler.log_and_continue(
                    "定期性能统计",
                    lambda: performance_info_service.calculate_and_save_performance_stats(job_id),
                    job_id=job_id
                )
        except asyncio.CancelledError:
            pass
    
    # 创建所有后台任务
    return [
        asyncio.create_task(flush_cache_periodically()),
        asyncio.create_task(update_performance_periodically()),
        asyncio.create_task(cancel_on_job_deleted())
    ]


async def _finalize_incomplete_requests(job_id: int, max_retries: int):
    """执行兜底处理逻辑"""
    updated_incomplete = await curd.batch_requests_curd.finalize_incomplete_requests_for_job(job_id, max_retries)
    if updated_incomplete:
        logger.info(f"作业 {job_id} 条件兜底处理：共处理 {updated_incomplete} 个非终态请求（可能包含成功修复）。")


async def _finalize_job_processing(job: BatchJob, job_details: dict, end_time: str):
    """执行作业最终处理和状态更新"""
    total = job_details.get('total_requests') or 0
    succ = 0
    fail = 0
    
    try:
        # 执行收尾兜底处理，将剩余非终态请求标记为失败
        forced = await curd.batch_requests_curd.finalize_all_incomplete_requests_for_job(job.id)
        if forced:
            logger.info(f"作业 {job.id} 收尾兜底处理：共处理 {forced} 个非终态请求（可能包含成功修复）。")
        
        # 统一进行状态统计和作业数据更新
        status_counts = await curd.batch_requests_curd.get_status_counts_for_job(job.id)
        succ = int(status_counts.get('success', 0))
        fail = int(status_counts.get('failed', 0))
        
        # 对齐总请求数：以实际请求行数为准
        actual_total = await curd.batch_requests_curd.count_requests_for_job(job.id)
        reported_total = job_details.get('total_requests') or job.total_requests
        if reported_total != actual_total:
            await curd.batch_job_curd.update_job_total_requests(job.id, actual_total)
            total = actual_total
            logger.warning(f"作业 {job.id} 的总请求数已从 {reported_total} 校正为 {actual_total}。")
        
        # 同步作业统计
        await curd.batch_job_curd.update_job_stats(job.id, succ, fail)
        logger.info(f"作业 {job.id} 统计信息已更新: {succ} 个成功, {fail} 个失败。")
        
    except Exception as e:
        logger.error(f"作业 {job.id} 收尾处理失败: {e}")

    # 根据终态数量判断是否完成：仅当成功+失败 == 总数 才标记完成，否则标记为失败
    # 特殊情况：空作业（total=0）应被视为已完成
    if (succ + fail >= total and total > 0) or total == 0:
        await curd.batch_job_curd.update_job_status(job.id, JobStatus.COMPLETED, end_time=end_time)
        logger.info(f"作业 {job.id} 已完成。")
    else:
        await curd.batch_job_curd.update_job_status(job.id, JobStatus.FAILED, end_time=end_time)
        logger.warning(f"作业 {job.id} 未全部完成（成功 {succ} / 失败 {fail} / 总计 {total}），已标记为失败。")


async def process_job(job_dict: dict):
    """处理单个批处理作业。"""
    job = BatchJob.model_validate(job_dict)
    logger.info(f"正在处理作业 {job.id}: '{job.batch_name}'")

    start_time = TimeUtils.get_current_time_iso()
    await curd.batch_job_curd.update_job_status(job.id, JobStatus.PROCESSING, start_time=start_time)

    # 从job对象中获取api_info_id，而不是从原始字典
    api_config_dict = await curd.api_info_curd.get_api_config_by_id(job.api_info_id)
    if not api_config_dict or not api_config_dict.get('is_active'):
        error_msg = f"作业 {job.id} 失败: 未找到API配置 '{job_dict['api_alias']}' 或该配置未激活。"
        logger.error(error_msg)
        await curd.error_logs_curd.log_error_to_db(job.id, None, ErrorType.CONFIGURATION_ERROR, error_msg)
        await curd.batch_job_curd.update_job_status(job.id, JobStatus.FAILED, end_time=datetime.now().isoformat())
        return
    api_config = APIInfo.model_validate(api_config_dict)

    # 初始化请求缓存
    request_cache = RequestCache()
    await request_cache.load_requests_for_job(job.id)
    
    requests_to_process = request_cache.get_pending_requests()

    if not requests_to_process:
        logger.info(f"作业 {job.id} 未发现待处理的请求。正在完成作业。")
        await curd.batch_job_curd.update_job_status(job.id, JobStatus.COMPLETED, end_time=datetime.now().isoformat())
        # 即使没有请求也要更新统计
        await performance_info_service.calculate_and_save_performance_stats(job.id)
        return

    semaphore = asyncio.Semaphore(job.concurrency)
    # 为每个请求创建 Task（而非裸协程），便于在作业删除时集中取消
    tasks = [
        asyncio.create_task(
            execute_request(
                req,
                job,
                api_config,
                semaphore,
                request_cache
            )
        )
        for req in requests_to_process
    ]

    # 创建后台任务组
    background_tasks = await _create_background_tasks(job.id, request_cache, tasks)
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 记录任务中的异常，但不提前关闭资源，确保所有任务自然收尾
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"作业 {job.id} 的任务 {idx} 遇到异常: {type(res).__name__}: {res}")
    except Exception as e:
        logger.error(f"处理作业 {job.id} 时发生错误: {e}", exc_info=True)
    finally:
        # 统一清理后台任务
        await TaskManager.cancel_tasks_safely(background_tasks, f"作业{job.id}后台任务组")
        
        # 最后一次刷新确保所有更新都写入数据库
        await request_cache.flush_updates(force=True)
        
        # 执行统一的兜底处理，避免重复操作
        await ErrorHandler.log_and_continue(
            "兜底处理",
            lambda: _finalize_incomplete_requests(job.id, job.max_retries),
            job_id=job.id
        )

    end_time = TimeUtils.get_current_time_iso()
    
    # 检查作业是否仍然存在
    job_details = await JobValidator.get_job_details_safe(job.id)
    if not job_details:
        # 作业在运行过程中被删除，终止后续统计与状态更新，避免产生未找到作业的告警
        logger.info(f"作业 {job.id} 在处理过程中已被删除，跳过最终统计与状态更新。")
        return
    
    # 再次确认作业仍然存在后再计算最终性能统计
    if await JobValidator.check_job_exists(job.id):
        await ErrorHandler.log_and_continue(
            "最终性能统计",
            lambda: performance_info_service.calculate_and_save_performance_stats(job.id),
            job_id=job.id
        )

    # 执行最终的收尾处理和状态更新
    await _finalize_job_processing(job, job_details, end_time)