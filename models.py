# models.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from const import JobStatus, RequestStatus

# Pydantic模型用于数据校验和结构化

class APIInfoBase(BaseModel):
    alias: str = Field(..., description="API配置的唯一别名")
    api_key: str
    api_base: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    is_active: bool = True

class APIInfo(APIInfoBase):
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True

class BatchJobBase(BaseModel):
    batch_name: str
    file_name: Optional[str] = None
    total_requests: int = 0
    status: str = JobStatus.PENDING
    api_info_id: int
    concurrency: int
    max_retries: int

class BatchJob(BatchJobBase):
    id: int
    success_count: int = 0
    failed_count: int = 0
    create_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    update_time: datetime

    class Config:
        from_attributes = True

class BatchRequestBase(BaseModel):
    batch_job_id: int
    request_index: int
    messages: List[Dict[str, Any]]
    status: str = RequestStatus.PENDING

class BatchRequest(BatchRequestBase):
    id: int
    retry_count: int = 0
    response_body: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    create_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    update_time: datetime

    class Config:
        from_attributes = True

class ErrorLog(BaseModel):
    id: int
    batch_job_id: Optional[int] = None
    request_id: Optional[int] = None
    error_type: str
    error_message: str
    error_details: Optional[str] = None
    create_time: datetime

    class Config:
        from_attributes = True

class PerformanceStats(BaseModel):
    id: int
    batch_job_id: int
    avg_response_time: Optional[float] = None
    total_processing_time: Optional[float] = None
    requests_per_second: Optional[float] = None
    total_cost: Optional[float] = None
    pricing_info: Optional[str] = None
    create_time: datetime

    class Config:
        from_attributes = True
