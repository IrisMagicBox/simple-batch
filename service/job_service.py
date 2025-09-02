"""
作业服务模块，负责作业的创建、管理和操作。
"""

import json
from io import BytesIO
from tempfile import SpooledTemporaryFile
from typing import Optional, Dict, Any

import ijson

import curd.api_info_curd
import curd.batch_job_curd
import curd.batch_requests_curd
import database as db
from const import JobStatus, RequestStatus
from const import JobStatus, RequestStatus
from core.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


# ==================== 作业创建相关函数 ====================

async def create_job_from_file(file_obj: SpooledTemporaryFile, batch_name: str, api_alias: str,
                              concurrency: int, max_retries: int) -> Optional[Dict[str, Any]]:
    """
    从上传的JSON文件创建批处理任务
    支持格式：
    [
        [
            {"role": "user", "content": "Hello"}
        ],
        [
            {"role": "system", "content": "happy"},
            {"role": "user", "content": "hello"}
        ]
    ]
    """
    try:
        # 基础校验与上限保护（与前端一致，双层兜底）
        CONCURRENCY_CAP = 200
        ATTEMPTS_CAP = 20
        try:
            concurrency = int(concurrency)
        except Exception:
            concurrency = 1
        try:
            max_retries = int(max_retries)
        except Exception:
            max_retries = 1
        if concurrency < 1:
            concurrency = 1
        if max_retries < 1:
            max_retries = 1
        if concurrency > CONCURRENCY_CAP:
            logger.info(f"--- 服务: 并发数过大，已从 {concurrency} 限制为 {CONCURRENCY_CAP} ---")
            concurrency = CONCURRENCY_CAP
        if max_retries > ATTEMPTS_CAP:
            logger.info(f"--- 服务: 总尝试次数过大，已从 {max_retries} 限制为 {ATTEMPTS_CAP} ---")
            max_retries = ATTEMPTS_CAP
        # 获取API配置
        logger.info(f"--- 服务: 正在获取别名 '{api_alias}' 的API配置 ---")
        api_config = await curd.api_info_curd.get_api_config_by_alias(api_alias)
        if not api_config:
            logger.error(f"--- 服务错误: 未找到API配置 '{api_alias}' ---")
            raise ValueError(f"API配置 '{api_alias}' 不存在")
        logger.info(f"--- 服务: 已找到API配置 ---")

        # 创建批处理任务
        logger.info(f"--- 服务: 正在数据库中创建批处理任务记录 ---")
        job_id = await curd.batch_job_curd.create_batch_job(
            batch_name=batch_name,
            file_name=file_obj.name if hasattr(file_obj, 'name') else batch_name,
            total_requests=0,  # 初始为0，后续更新
            api_info_id=api_config.get('id') if isinstance(api_config, dict) else api_config["id"],
            concurrency=concurrency,
            max_retries=max_retries
        )
        logger.info(f"--- 服务: 批处理任务记录已创建，ID: {job_id} ---")

        # 使用ijson进行流式解析
        if isinstance(file_obj, bytes):
            file_obj = BytesIO(file_obj)
        else:
            file_obj.seek(0)  # 确保从文件开头开始读取
        requests_parser = ijson.items(file_obj, 'item')

        requests_batch = []
        batch_size = 1000  # 每1000条请求批量插入一次
        request_index = 0

        logger.info(f"--- 服务: 开始解析文件 ---")
        for messages_array in requests_parser:
            request_index += 1

            # 验证消息格式
            if not isinstance(messages_array, list):
                raise ValueError(f"请求 {request_index} 格式错误：应该是消息数组")

            # 验证每条消息的格式
            for i, message in enumerate(messages_array):
                if not isinstance(message, dict) or 'role' not in message or 'content' not in message:
                    raise ValueError(f"请求 {request_index} 中的消息 {i+1} 格式错误：缺少 role 或 content 字段")

            # 创建请求记录
            request_data = {
                'job_id': job_id,
                'request_index': request_index,
                'messages': messages_array,  # 直接存储解析后的列表
                'status': RequestStatus.PENDING,
                'retry_count': 0
            }
            requests_batch.append(request_data)

            if len(requests_batch) >= batch_size:
                logger.info(f"--- 服务: 正在插入 {len(requests_batch)} 个请求的批次... ---")
                await curd.batch_requests_curd.bulk_insert_requests(requests_batch)
                logger.info(f"--- 服务: 批次插入成功。当前总数: {request_index} ---")
                requests_batch = []

        # 插入剩余的请求
        if requests_batch:
            logger.info(f"--- 服务: 正在插入最后 {len(requests_batch)} 个请求的批次... ---")
            await curd.batch_requests_curd.bulk_insert_requests(requests_batch)
            logger.info(f"--- 服务: 最后批次插入成功。请求总数: {request_index} ---")
            requests_batch = []

        logger.info("--- 服务: 文件解析和请求创建完成。 ---")

        # 更新任务的总请求数
        await curd.batch_job_curd.update_job_total_requests(job_id, request_index)

        logger.info(f"--- 服务: 任务创建完成。任务ID: {job_id}, 总请求数: {request_index} ---")
        return {"job_id": job_id, "total_requests": request_index}

    except json.JSONDecodeError as e:
        # 如果创建了任务但解析失败，需要清理
        if 'job_id' in locals():
            await curd.batch_job_curd.delete_job(job_id)
        logger.error(f"--- 服务错误: 作业 {job_id} 的JSON文件解析失败: {e} ---")
        raise ValueError(f"JSON文件格式错误: {str(e)}")
    except Exception as e:
        # 如果创建了任务但处理失败，需要清理
        if 'job_id' in locals():
            await curd.batch_job_curd.delete_job(job_id)
        logger.error(f"--- 服务错误: 处理作业 {job_id} 的文件时发生错误: {e} ---")
        raise e


# ==================== 作业管理相关函数 ====================

async def delete_job(job_id: int) -> bool:
    """
    删除作业及其所有关联的请求记录
    
    Args:
        job_id: 作业ID
        
    Returns:
        bool: 删除是否成功
    """
    try:
        await curd.batch_job_curd.delete_job(job_id)
        return True
    except Exception as e:
        logger.error(f"删除作业 {job_id} 时出错: {e}")
        return False


async def retry_failed_requests(job_id: int) -> bool:
    """
    重试指定作业的所有失败请求
    
    Args:
        job_id: 作业ID
        
    Returns:
        bool: 重试操作是否成功
    """
    try:
        # 1) 优先重置失败请求为 pending
        updated_failed = await curd.batch_requests_curd.reset_failed_requests_for_job(job_id)

        if updated_failed > 0:
            await curd.batch_job_curd.update_job_status(job_id, JobStatus.PENDING)
            logger.info(f"已将作业 {job_id} 的 {updated_failed} 个失败请求重置为待处理状态")
            return True

        # 2) 若没有失败请求，但存在 processing/retrying 的未完成请求，则一并重置为 pending
        updated_inprogress = await curd.batch_requests_curd.reset_processing_requests_for_job(job_id)
        if updated_inprogress > 0:
            await curd.batch_job_curd.update_job_status(job_id, JobStatus.PENDING)
            logger.info(f"未发现失败请求，已将作业 {job_id} 的 {updated_inprogress} 个进行中的请求重置为待处理状态")
            return True

        # 3) 两者都没有需要重置的请求，保持现状
        logger.info(f"未发现可重试的请求（失败或进行中）: 作业 {job_id}")
        return True
    except Exception as e:
        logger.error(f"重试作业 {job_id} 的失败请求时出错: {e}")
        return False


async def retry_specific_request(request_id: int) -> bool:
    """
    重试指定的单个请求
    
    Args:
        request_id: 请求ID
        
    Returns:
        bool: 重试操作是否成功
    """
    try:
        success = await curd.batch_requests_curd.reset_single_request(request_id)
        return success
    except Exception as e:
        logger.error(f"重试请求 {request_id} 时出错: {e}")
        return False


async def reset_job_to_pending(job_id: int) -> bool:
    """
    将作业重置为待处理状态，所有请求重置为pending
    
    Args:
        job_id: 作业ID
        
    Returns:
        bool: 重置操作是否成功
    """
    try:
        # 将所有请求重置为pending
        await curd.batch_requests_curd.reset_all_requests_for_job(job_id)
        
        # 将作业状态重置为pending
        await curd.batch_job_curd.update_job_status(job_id, JobStatus.PENDING)
        
        # 重置作业统计信息
        await curd.batch_job_curd.reset_job_stats(job_id)
            
        return True
    except Exception as e:
        logger.error(f"将作业 {job_id} 重置为待处理状态时出错: {e}")
        return False


# ==================== 暂停/恢复相关函数 ====================

async def pause_job(job_id: int) -> bool:
    """
    将作业状态设置为 paused。
    - 若作业尚未开始：调度器不会再拾取该作业。
    - 若作业正在运行：执行器在每次请求尝试前会检测到 paused 并等待，达到协作式暂停效果。
    """
    try:
        await curd.batch_job_curd.update_job_status(job_id, JobStatus.PAUSED)
        return True
    except Exception as e:
        logger.error(f"暂停作业 {job_id} 时出错: {e}")
        return False


async def resume_job(job_id: int) -> bool:
    """
    恢复已暂停的作业。
    - 将状态统一设置为 pending，便于调度器再次拾取并创建处理任务。
    - 同时将可能处于 processing/retrying 的请求重置为 pending，避免作业被卡死。
    """
    try:
        job = await curd.batch_job_curd.get_job_details(job_id)
        if not job:
            return False
        if job.get('status') != JobStatus.PAUSED:
            return True
        # 将可能残留的processing/retrying请求重置为pending（幂等）
        try:
            await curd.batch_requests_curd.reset_processing_requests_for_job(job_id)
        except Exception:
            # 安全起见，忽略该步骤的异常，不影响后续状态恢复
            pass
        # 统一恢复为pending，让调度器拾取并重新创建任务
        await curd.batch_job_curd.update_job_status(job_id, JobStatus.PENDING)
        return True
    except Exception as e:
        logger.error(f"恢复作业 {job_id} 时出错: {e}")
        return False