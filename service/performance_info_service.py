import json
from datetime import datetime
 

import curd.batch_job_curd
import curd.error_logs_curd
import curd.performance_curd
import curd.batch_requests_curd
from const import RequestStatus, ErrorType
from core.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


async def _save_empty_performance_stats(job_id: int, job_details: dict):
    """保存空的性能统计数据"""
    pricing_info = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_cost": 0.0,
        "completion_cost": 0.0,
        "model": (job_details.get('api') or {}).get('model_name') or job_details.get('model_name', 'unknown')
    }
    await curd.performance_curd.upsert_performance(
        job_id=job_id,
        avg_response_time=0.0,
        total_processing_time=0.0,
        rps=0.0,
        total_cost=0.0,
        pricing_info=json.dumps(pricing_info)
    )
    logger.info(f"作业 {job_id} 没有成功的请求，已写入空的性能统计记录。")


async def calculate_and_save_performance_stats(job_id: int):
    """计算并存储作业的性能统计数据。"""
    try:
        # 获取作业详情
        job_details = await curd.batch_job_curd.get_job_details(job_id)
        if not job_details:
            logger.warning(f"未找到作业 {job_id}。")
            return

        total_requests = job_details.get('total_requests') or 0

        # 获取成功请求的最早开始时间和最晚结束时间
        earliest_start_and_end_time = await curd.batch_requests_curd.get_earliest_start_and_end_time_for_success_requests(
            job_id)
        
        # 如果没有任何成功请求，则写入一条空的性能记录（全为0），以便前端有可见数据
        if not earliest_start_and_end_time or not earliest_start_and_end_time.get('earliest_start_time') or not earliest_start_and_end_time.get('latest_end_time'):
            await _save_empty_performance_stats(job_id, job_details)
            return

        # 将字符串转换为 datetime 对象
        batch_start_time = datetime.fromisoformat(earliest_start_and_end_time['earliest_start_time'])
        batch_end_time = datetime.fromisoformat(earliest_start_and_end_time['latest_end_time'])

        # 计算总秒数
        total_success_seconds = (batch_end_time - batch_start_time).total_seconds()

        if total_success_seconds <= 0:
            logger.warning(f"作业 {job_id} 的总处理时间无效。将使用0填充。")
            total_success_seconds = 0.0

        # 计算单请求平均耗时：直接从数据库获取成功的请求
        successful_requests = await curd.batch_requests_curd.get_requests_for_job(job_id, status=RequestStatus.SUCCESS)
        if not successful_requests:
            # 理论上前面的分支已经处理，这里兜底
            await _save_empty_performance_stats(job_id, job_details)
            return

        durations = []
        for req in successful_requests:
            try:
                st = datetime.fromisoformat(req['start_time']) if req.get('start_time') else None
                et = datetime.fromisoformat(req['end_time']) if req.get('end_time') else None
                if st and et and et >= st:
                    durations.append((et - st).total_seconds())
            except Exception:
                continue

        avg_response_time = (sum(durations) / len(durations)) if durations else 0.0

        # RPS 定义为 成功请求吞吐量 / 成功请求墙钟时间
        rps = (len(successful_requests) / total_success_seconds) if total_success_seconds > 0 else 0.0

        total_prompt_tokens = sum(req.get('prompt_tokens', 0) for req in successful_requests)
        total_completion_tokens = sum(req.get('completion_tokens', 0) for req in successful_requests)

        # 读取API计费配置（精简：仅 token 计费）
        api_cfg = (job_details.get('api') or {}) if isinstance(job_details, dict) else {}
        currency = api_cfg.get('currency') or 'RMB'
        prompt_price_per_1k = float(api_cfg.get('prompt_price_per_1k') or 0.0)
        completion_price_per_1k = float(api_cfg.get('completion_price_per_1k') or 0.0)

        # 成本计算：仅根据输入/输出token按千计费，无最小计费单位
        prompt_cost = (total_prompt_tokens / 1000.0) * prompt_price_per_1k
        completion_cost = (total_completion_tokens / 1000.0) * completion_price_per_1k
        total_cost = float(prompt_cost + completion_cost)

        pricing_info = {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "currency": currency,
            "billing_mode": "token",
            "model": (job_details.get('api') or {}).get('model_name') or job_details.get('model_name', 'unknown'),
            "total_requests": total_requests,
            "successful_requests": len(successful_requests)
        }

        # 保存/更新性能统计
        await curd.performance_curd.upsert_performance(
            job_id=job_id,
            avg_response_time=avg_response_time,
            total_processing_time=total_success_seconds,
            rps=rps,
            total_cost=total_cost,
            pricing_info=json.dumps(pricing_info)
        )

        logger.info(f"作业 {job_id} 的性能统计数据计算并保存成功。")

    except Exception as e:
        logger.error(f"计算作业 {job_id} 的性能统计数据时出错: {e}", exc_info=True)
        await curd.error_logs_curd.log_error_to_db(job_id, None, ErrorType.PERFORMANCE_CALCULATION_ERROR, str(e))
