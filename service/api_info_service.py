from typing import Dict, Any, Optional

import curd.api_info_curd


async def get_all_api_configs_for_ui():
    return await curd.api_info_curd.get_all_api_configs()


async def get_active_aliases():
    """获取所有激活的API别名列表（服务层封装）。"""
    configs = await curd.api_info_curd.get_active_api_configs()
    return [c.get('alias') for c in configs if c.get('alias')]


async def add_api_config(alias: str, api_key: str, api_base: str, model_name: str,
                        max_tokens: int = 4096, temperature: float = 0.7, timeout: int = 60,
                        currency: str = 'USD', billing_mode: str = 'token',
                        prompt_price_per_1k: float = 0.0, completion_price_per_1k: float = 0.0,
                        request_price: float = 0.0, second_price: float = 0.0,
                        minimum_billable_unit: int = 1, pricing_notes: Optional[str] = None,
                        is_active: int = 1):
    return await curd.api_info_curd.create_api_config(
        alias, api_key, api_base, model_name, max_tokens, temperature, timeout,
        currency, billing_mode, prompt_price_per_1k, completion_price_per_1k,
        request_price, second_price, minimum_billable_unit, pricing_notes, is_active
    )


async def update_api_config_from_ui(config_id: int, updates: Dict[str, Any]):
    return await curd.api_info_curd.update_api_config(config_id, updates)


async def delete_api_config_from_ui(config_id: int):
    return await curd.api_info_curd.delete_api_config(config_id)


async def get_api_config_by_id(config_id: int) -> Optional[Dict[str, Any]]:
    return await curd.api_info_curd.get_api_config_by_id(config_id)
