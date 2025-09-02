"""
API请求执行器模块，负责执行单个API请求。
"""

import asyncio
import json
import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError
from datetime import datetime
from typing import Dict, Any, Optional, List

from models import BatchRequest, BatchJob, APIInfo
import curd.error_logs_curd
import curd.batch_job_curd
from processor.request_cache import RequestCache
from processor.utils import JobValidator, TimeUtils
from const import RequestStatus
from core.logger import get_logger
import settings

# 获取日志记录器
logger = get_logger(__name__)


def process_response_data(response_body: str) -> Dict[str, Any]:
    """
    处理响应数据（现在直接在协程中调用）
    实际应用中可以在这里进行更复杂的处理，例如：
    - 提取特定字段
    - 进行数据转换
    - 执行计算
    """
    try:
        data = json.loads(response_body)
        # 提取关键信息
        usage = data.get('usage', {}) if isinstance(data, dict) else {}
        choices = data.get('choices', []) if isinstance(data, dict) else []
        
        # 计算一些基本指标
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        return {
            'processed': True,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }
    except Exception as e:
        return {
            'processed': False,
            'error': str(e)
        }


async def wait_if_job_paused(job_id: int, check_interval: float = None):
    """如果作业被暂停，则等待直到恢复。
    周期性查询数据库中的作业状态，若为 paused 则阻塞等待。
    """
    if check_interval is None:
        check_interval = settings.JOB_PAUSE_CHECK_INTERVAL
    await JobValidator.wait_if_job_paused(job_id, check_interval)


async def check_job_exists(job_id: int) -> bool:
    """检查作业是否存在（用于减少重复查询）"""
    return await JobValidator.check_job_exists(job_id)


async def execute_request(
    request: BatchRequest, 
    job: BatchJob, 
    api_config: APIInfo, 
    semaphore: asyncio.Semaphore, 
    cache: RequestCache
):
    """执行单个API请求，包含重试逻辑。"""
    async with semaphore:
        request_id = request.id
        # max_retries 为重试次数，不包含首次尝试。
        max_attempts = max(1, job.max_retries)

        client = AsyncOpenAI(
            api_key=api_config.api_key,
            base_url=api_config.api_base,
        )

        # 尝试总次数为 max_attempts，attempt 为 0-based 下标
        for attempt in range(max_attempts):
            # 在每次尝试开始时统一检查作业状态
            await wait_if_job_paused(job.id)
            
            # 检查作业是否存在，避免作业删除后仍继续执行
            if not await check_job_exists(job.id):
                logger.info(f"作业 {job.id} 已被删除，停止执行请求 {request_id}。")
                return
            start_time = TimeUtils.get_current_time_iso()
            try:
                status_to_set = RequestStatus.PROCESSING if attempt == 0 else RequestStatus.RETRYING
                cache.update_request_status(request_id, status=status_to_set, start_time=start_time)

                response = await client.chat.completions.create(
                    model=api_config.model_name,
                    messages=request.messages,
                    max_tokens=api_config.max_tokens,
                    temperature=api_config.temperature,
                    timeout=httpx.Timeout(api_config.timeout)
                )

                end_time = TimeUtils.get_current_time_iso()
                response_body = response.model_dump_json()
                usage = response.usage

                # 直接在协程中处理响应数据
                processed_data = process_response_data(response_body)
                
                if processed_data.get('processed'):
                    logger.info(f"请求 {request_id} 的响应数据已处理")
                else:
                    logger.warning(f"请求 {request_id} 的响应数据处理失败: {processed_data.get('error')}")

                # 统一更新请求为成功状态，包含处理后的数据
                cache.update_request_as_success(
                    request_id=request_id,
                    response_body=response_body,
                    p_tokens=usage.prompt_tokens if usage else 0,
                    c_tokens=usage.completion_tokens if usage else 0,
                    end_time=end_time,
                    processed_data=processed_data
                )
                logger.info(f"请求 {request_id} (作业 {job.id}) 已成功。")
                return

            except (APIError, APITimeoutError) as e:
                end_time = TimeUtils.get_current_time_iso()
                error_type = type(e).__name__
                error_message = str(e)
                logger.warning(f"请求 {request_id} (作业 {job.id}) 在第 {attempt + 1}/{max_attempts} 次尝试时失败: {error_type}")

                await curd.error_logs_curd.log_error_to_db(
                    job_id=job.id,
                    request_id=request_id,
                    error_type=error_type,
                    error_message=error_message,
                    error_details=json.dumps(e.body) if hasattr(e, 'body') and e.body else None
                )

                # 若仍有剩余尝试次数，则标记为重试中；否则标记为最终失败
                if attempt < max_attempts - 1:
                    # 在下一次重试前检查是否被暂停和作业是否仍然存在
                    await wait_if_job_paused(job.id)
                    if not await check_job_exists(job.id):
                        logger.info(f"作业 {job.id} 已被删除，停止对请求 {request_id} 的后续重试。")
                        return
                    cache.update_request_as_failed(request_id, end_time, new_retry_count=attempt + 1,
                                                  final_status=RequestStatus.RETRYING)
                    await asyncio.sleep(settings.RETRY_BACKOFF_BASE ** attempt)
                else:
                    cache.update_request_as_failed(request_id, end_time, new_retry_count=attempt + 1)
                    logger.error(f"请求 {request_id} (作业 {job.id}) 在共 {max_attempts} 次尝试后永久失败。")
                    return

            except Exception as e:
                end_time = TimeUtils.get_current_time_iso()
                error_type = type(e).__name__
                error_message = str(e)
                logger.error(f"请求 {request_id} (作业 {job.id}) 发生未预期的错误: {error_type}", exc_info=True)
                await curd.error_logs_curd.log_error_to_db(
                    job_id=job.id,
                    request_id=request_id,
                    error_type=error_type,
                    error_message=error_message
                )
                cache.update_request_as_failed(request_id, end_time, new_retry_count=attempt + 1)
                return