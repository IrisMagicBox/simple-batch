from curd import batch_job_curd as batch_jobs_curd
from curd import batch_requests_curd
from curd import error_logs_curd


async def get_dashboard_summary():
    """获取仪表盘所需的所有作业摘要。"""
    jobs = await batch_jobs_curd.get_all_jobs_summary()
    # 为所有作业补齐实时统计，确保进度与成功/失败一致
    try:
        for job in jobs:
            job_id = job.get('id')
            total = await batch_requests_curd.count_requests_for_job(job_id)
            status_counts = await batch_requests_curd.get_status_counts_for_job(job_id)
            success_count = int(status_counts.get('success', 0))
            failed_count = int(status_counts.get('failed', 0))
            job['total_requests'] = total if total is not None else job.get('total_requests')
            job['success_count'] = success_count
            job['failed_count'] = failed_count
    except Exception:
        # 出错时返回原始摘要
        pass
    return jobs


async def get_job_details_for_ui(job_id: int):
    """获取单个作业的详细信息以在UI中显示。"""
    job = await batch_jobs_curd.get_job_details(job_id)
    if not job:
        return None
    try:
        # 计算实时的成功/失败/总数，便于运行中刷新看到进度
        total = await batch_requests_curd.count_requests_for_job(job_id)
        status_counts = await batch_requests_curd.get_status_counts_for_job(job_id)
        success_count = int(status_counts.get('success', 0))
        failed_count = int(status_counts.get('failed', 0))
        # 覆盖/补充返回给UI的统计字段
        job['total_requests'] = total if total is not None else job.get('total_requests')
        job['success_count'] = success_count
        job['failed_count'] = failed_count
        job['in_progress_count'] = max(0, (total or 0) - success_count - failed_count)
    except Exception:
        # 若统计失败则原样返回
        pass
    return job


async def get_job_time_series_for_ui(job_id: int, interval_ms: int = 60000):
    """获取用于UI折线图展示的时间序列统计，支持可调粒度。"""
    return await batch_requests_curd.get_time_series_counts(job_id, interval_ms)


async def get_job_requests_page(job_id: int, page: int, page_size: int = 2):
    """分页获取作业的请求明细（messages 与 response_body）。
    返回：{
      'items': [ {id, request_index, messages, response_body, status, ...}, ...],
      'total': int,
      'page': int,
      'page_size': int,
      'total_pages': int
    }
    """
    if page is None or page < 1:
        page = 1
    if page_size is None or page_size < 1:
        page_size = 2
    total = await batch_requests_curd.count_requests_for_job(job_id)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    items = await batch_requests_curd.get_requests_for_job_paginated(job_id, page_size, offset)
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }


async def get_job_errors_page(job_id: int, page: int, page_size: int = 20):
    """分页获取作业的错误日志。
    返回：{
      'items': [ {id, request_id, error_type, error_message, error_details, create_time}, ...],
      'total': int,
      'page': int,
      'page_size': int,
      'total_pages': int
    }
    """
    if page is None or page < 1:
        page = 1
    if page_size is None or page_size < 1:
        page_size = 20
    total = await error_logs_curd.count_errors_for_job(job_id)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    items = await error_logs_curd.get_errors_for_job_paginated(job_id, page_size, offset)
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }
    


async def get_request_detail(request_id: int):
    """获取单条请求详情。"""
    return await batch_requests_curd.get_request_by_id(request_id)


async def get_requests_by_time_bucket(job_id: int, bucket: str, interval_ms: int, category: str):
    """获取某作业在时间桶与类别下的请求列表。category in ['requests','success','failed']"""
    return await batch_requests_curd.get_requests_by_time_bucket(job_id, bucket, interval_ms, category)
