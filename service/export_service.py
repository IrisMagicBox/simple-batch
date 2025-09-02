"""
导出服务模块，负责将任务结果导出为JSON文件。
"""

import json
import os
from typing import List, Dict, Any

import curd.batch_requests_curd
from const import RequestStatus
from core.logger import get_logger

logger = get_logger(__name__)


async def export_job_results_to_json(job_id: int, batch_name: str) -> str:
    """
    将指定作业的所有成功请求结果导出为JSON文件。
    
    Args:
        job_id: 作业ID
        batch_name: 作业名称，用作导出文件前缀
        
    Returns:
        str: 导出文件的完整路径（项目 data 目录），用于浏览器下载
    """
    try:
        # 获取作业的所有请求，按request_index排序
        requests = await curd.batch_requests_curd.get_requests_for_job(job_id, status=RequestStatus.SUCCESS)
        
        # 按request_index排序
        requests.sort(key=lambda x: x['request_index'])
        
        # 构造导出数据
        export_data = []
        for req in requests:
            export_data.append({
                'messages': req['messages'],
                'response_body': req['response_body']
            })
        # 计算项目根目录（当前文件: project/service/export_service.py -> 根目录上上级）
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # 简单清洗文件名，避免非法字符/路径分隔符
        safe_name = str(batch_name).strip().replace(os.sep, '_').replace('..', '_') or 'export'
        filename = os.path.join(data_dir, f"{safe_name}.json")

        # 覆盖式导出
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"作业 {job_id} 的结果已导出到 {filename}")
        return filename
    except Exception as e:
        logger.error(f"导出作业 {job_id} 结果时出错: {e}")
        raise