"""
通用UI工具：掩码、Markdown构建、数值校验与限制。
"""
from __future__ import annotations
from typing import Dict, Tuple, Any, Optional


def mask_api_key(value: Optional[str]) -> str:
    """遮蔽 API Key：保留前4位与后4位，中间固定12个*；长度不足时全部用*。
    """
    if not value:
        return ""
    s = str(value)
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}{'*'*12}{s[-4:]}"


def _fmt_price(v: Any) -> str:
    try:
        if v is None:
            return "-"
        return f"{float(v):.6f}"
    except Exception:
        return str(v)


def build_billing_markdown(config: Dict[str, Any]) -> str:
    """根据配置构建计费信息 Markdown 文本。"""
    currency = config.get("currency") or "RMB"
    prompt_price = config.get("prompt_price_per_1k")
    completion_price = config.get("completion_price_per_1k")
    pricing_notes = config.get("pricing_notes") or ""
    billing_mode = config.get("billing_mode") or "token"

    md = f"""
**别名**：{config.get('alias','')}

**计费模式**：{billing_mode}

**币种**：{currency}

**每1K输入Token单价**：{_fmt_price(prompt_price)}

**每1K输出Token单价**：{_fmt_price(completion_price)}

**价格备注**：{pricing_notes or '-'}
"""
    return md


def cap_concurrency_attempts(concurrency: Any, attempts: Any,
                             max_concurrency: int = 200,
                             max_attempts: int = 20) -> Tuple[int, int, list[str]]:
    """将并发与尝试次数转换为 int、做下限1与软上限限制，返回(并发, 尝试次数, 警告列表)。"""
    warnings: list[str] = []
    try:
        c = int(concurrency)
    except Exception:
        c = 1
    try:
        a = int(attempts)
    except Exception:
        a = 1
    if c < 1:
        c = 1
    if a < 1:
        a = 1
    if c > max_concurrency:
        warnings.append(f"并发数过大，已从 {c} 限制为 {max_concurrency}。大并发可能导致速率限制或失败率上升。")
        c = max_concurrency
    if a > max_attempts:
        warnings.append(f"总尝试次数过大，已从 {a} 限制为 {max_attempts}。过多重试可能引发雪崩重试负载。")
        a = max_attempts
    return c, a, warnings
