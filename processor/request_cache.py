"""
请求缓存模块，统一管理批处理请求的状态和响应数据，减少数据库访问压力。
"""

import time
from typing import Dict, List, Optional, Any

from models import BatchRequest
import curd.batch_requests_curd
from const import RequestStatus
import settings
from core.logger import get_logger


logger = get_logger(__name__)

class RequestCache:
    """统一缓存批处理请求的状态和响应数据，使用内存作为单一数据源"""
    
    def __init__(self):
        # 存储请求对象 - 内存中的主数据源
        self.requests: Dict[int, BatchRequest] = {}
        # 标记需要同步到数据库的请求ID集合
        self.dirty_request_ids: set[int] = set()
        # 批量更新大小
        self.batch_size = settings.REQUEST_CACHE_BATCH_SIZE
        # 上次批量更新时间
        self.last_flush_time = time.time()
        # 更新间隔（秒）
        self.flush_interval = settings.REQUEST_CACHE_FLUSH_INTERVAL
        
    async def load_requests_for_job(self, job_id: int):
        """从数据库加载作业的所有请求到缓存中"""
        requests_data = await curd.batch_requests_curd.get_requests_for_job(job_id)
        self.requests = {
            req['id']: BatchRequest.model_validate(req) 
            for req in requests_data
        }
        logger.info(f"已加载 {len(self.requests)} 个请求到作业 {job_id} 的缓存中")
        
    def get_pending_requests(self) -> List[BatchRequest]:
        """获取所有待处理的请求"""
        return [
            req for req in self.requests.values() 
            if req.status == RequestStatus.PENDING
        ]
        
    def update_request_status(self, request_id: int, status: str, start_time: Optional[str] = None):
        """更新请求状态（直接操作内存对象）"""
        if request_id in self.requests:
            self.requests[request_id].status = status
            if start_time:
                self.requests[request_id].start_time = start_time
            # 标记为需要同步
            self.dirty_request_ids.add(request_id)
            
    def update_request_as_success(self, request_id: int, response_body: str, 
                                 p_tokens: int, c_tokens: int, end_time: str,
                                 processed_data: Optional[Dict[str, Any]] = None):
        """更新请求为成功状态（直接操作内存对象）"""
        if request_id in self.requests:
            req = self.requests[request_id]
            req.status = RequestStatus.SUCCESS
            req.response_body = response_body
            req.prompt_tokens = p_tokens
            req.completion_tokens = c_tokens
            req.total_tokens = p_tokens + c_tokens
            req.end_time = end_time
            
            # 如果有处理后的数据，也一同更新
            if processed_data and processed_data.get('processed'):
                # 可以在这里执行额外的CPU密集型处理逻辑
                logger.info(f"请求 {request_id} 的响应数据已处理")
            
            # 标记为需要同步
            self.dirty_request_ids.add(request_id)
    def update_request_as_failed(self, request_id: int, end_time: str, 
                                new_retry_count: int, final_status: str = RequestStatus.FAILED):
        """更新请求为失败或重试状态（直接操作内存对象）"""
        if request_id in self.requests:
            req = self.requests[request_id]
            req.status = final_status
            req.retry_count = new_retry_count
            req.end_time = end_time
            # 标记为需要同步
            self.dirty_request_ids.add(request_id)
            
    async def flush_updates(self, force: bool = False):
        """将内存中的dirty请求批量同步到数据库
        Args:
            force: 为 True 时，无论批量大小或时间间隔，都会强制刷新。
        """
        if not self.dirty_request_ids:
            return

        current_time = time.time()
        # 满足批量大小、时间间隔，或强制刷新时执行
        if force or (
            len(self.dirty_request_ids) >= self.batch_size or 
            current_time - self.last_flush_time >= self.flush_interval
        ):
            # 获取需要同步的请求
            dirty_ids = list(self.dirty_request_ids)
            requests_to_sync = [self.requests[req_id] for req_id in dirty_ids if req_id in self.requests]
            
            # 清空dirty标记
            self.dirty_request_ids.clear()

            try:
                # 按状态分类并批量更新
                success_requests = [req for req in requests_to_sync if req.status == RequestStatus.SUCCESS]
                failed_requests = [req for req in requests_to_sync if req.status == RequestStatus.FAILED]
                processing_requests = [req for req in requests_to_sync if req.status in [RequestStatus.PROCESSING, RequestStatus.RETRYING]]

                # 批量执行数据库更新
                if success_requests:
                    await self._batch_update_success_requests(success_requests)
                if failed_requests:
                    await self._batch_update_failed_requests(failed_requests)
                if processing_requests:
                    await self._batch_update_processing_requests(processing_requests)

                # 成功后才更新时间戳
                self.last_flush_time = current_time
                logger.info(f"已将 {len(requests_to_sync)} 个请求的更新同步到数据库")
            except Exception as e:
                logger.error(f"同步更新到数据库时出错: {e}")
                # 出错时重新标记为dirty，但不更新last_flush_time
                self.dirty_request_ids.update(dirty_ids)
    
    async def _batch_update_success_requests(self, requests: List[BatchRequest]):
        """批量更新成功请求"""
        updates = []
        for req in requests:
            update_record = {
                'request_id': req.id,
                'status': req.status,
                'response_body': req.response_body,
                'prompt_tokens': req.prompt_tokens,
                'completion_tokens': req.completion_tokens,
                'start_time': req.start_time,
                'end_time': req.end_time
            }
            updates.append(update_record)
            # 添加调试日志，记录token和时间设置情况
            logger.debug(f"准备更新成功请求 {req.id}: prompt_tokens={req.prompt_tokens}, completion_tokens={req.completion_tokens}, total_tokens={req.total_tokens}, start_time={req.start_time}, end_time={req.end_time}")
        
        logger.info(f"批量更新 {len(updates)} 个成功请求到数据库，包含tokens和时间字段")
        await curd.batch_requests_curd.bulk_update_request_success(updates)
            
    async def _batch_update_failed_requests(self, requests: List[BatchRequest]):
        """批量更新失败请求"""
        updates = []
        for req in requests:
            update_record = {
                'request_id': req.id,
                'status': req.status,
                'retry_count': req.retry_count,
                'end_time': req.end_time
            }
            updates.append(update_record)
        await curd.batch_requests_curd.bulk_update_request_failure(updates)
        
    async def _batch_update_processing_requests(self, requests: List[BatchRequest]):
        """批量更新处理中请求"""
        updates = []
        for req in requests:
            update_record = {
                'request_id': req.id,
                'status': req.status,
                'start_time': req.start_time
            }
            updates.append(update_record)
        await curd.batch_requests_curd.bulk_update_request_status(updates)