"""
作业调度器模块，负责定期检查并处理待处理的作业。
"""

import asyncio
import time
from typing import List, Dict, Any

import curd.batch_job_curd
import curd.batch_requests_curd
from processor.job_processor import process_job
import database as db
from const import JobStatus
from core.logger import get_logger
import settings

# 获取日志记录器
logger = get_logger(__name__)


async def recover_incomplete_jobs():
    """恢复因程序崩溃而中断的作业和请求。"""
    logger.info("正在检查并恢复未完成的作业...")
    try:
        # 查找所有状态为 'processing' 的作业
        stuck_jobs = await curd.batch_job_curd.get_jobs_by_status(JobStatus.PROCESSING)
        
        # 查找所有状态为 'completed' 但有未完成请求的作业
        incomplete_completed_jobs = await curd.batch_job_curd.get_incomplete_completed_jobs()
        
        all_jobs_to_recover = stuck_jobs + incomplete_completed_jobs
        
        for job in all_jobs_to_recover:
            # 将该任务下所有 'processing' 或 'retrying' 的请求重置为 'pending'
            reset_count = await curd.batch_requests_curd.reset_processing_requests_for_job(job['id'])
            if reset_count > 0:
                logger.info(f"作业 {job['id']} 已恢复。{reset_count} 个请求已重置为待处理状态。")
            
            # 将作业状态重置为 'pending'
            await curd.batch_job_curd.update_job_status(job['id'], JobStatus.PENDING)
            logger.info(f"作业 {job['id']} 状态已重置为待处理。")
        
        # 重置completed状态但有未完成请求的作业的统计信息
        for job in incomplete_completed_jobs:
            await curd.batch_job_curd.reset_job_stats(job['id'])
            logger.info(f"作业 {job['id']} 统计信息已重置。")
        
        if not all_jobs_to_recover:
            logger.info("未发现需要恢复的作业。")
        else:
            logger.info(f"作业恢复完成。共处理了 {len(all_jobs_to_recover)} 个作业。")
            
    except Exception as e:
        logger.error(f"作业恢复过程中发生错误: {e}", exc_info=True)


async def scheduler():
    """调度器，定期检查并处理待处理的作业。"""
    logger.info("调度器已启动。开始查找待处理的作业")
    
    # 在主循环前运行一次恢复检查
    await recover_incomplete_jobs()
    
    # 记录上次恢复检查时间，避免频繁恢复
    last_recovery_time = time.time()

    while True:
        try:
            current_time = time.time()
            # 仅在超过恢复间隔时才执行恢复检查
            if current_time - last_recovery_time >= settings.SCHEDULER_RECOVERY_INTERVAL:
                await recover_incomplete_jobs()
                last_recovery_time = current_time

            job_dicts = await curd.batch_job_curd.get_pending_jobs_and_api_id()

            if job_dicts:
                logger.info(f"找到 {len(job_dicts)} 个待处理作业。正在创建处理任务。")
                # 为每个作业创建独立的任务，避免一个作业卡住影响其他作业
                for job_dict in job_dicts:
                    asyncio.create_task(process_job(job_dict))
                # 不等待任务完成，让它们在后台运行
                # 这样可以确保调度器能够继续检查新的待处理作业
            
            # 等待一段时间再进行下一次检查
            await asyncio.sleep(settings.SCHEDULER_POLLING_INTERVAL)

        except Exception as e:
            logger.error(f"调度器中发生错误: {e}", exc_info=True)
            await asyncio.sleep(settings.SCHEDULER_ERROR_RETRY_INTERVAL)  # 出错时等待更长时间再重试