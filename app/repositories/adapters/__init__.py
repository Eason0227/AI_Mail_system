"""外部資料格式 → 內部 Model 的轉換層。

每一種外部資料來源對應一個 Adapter：

    Mock JSON            -> MockMailAdapter
    公司 Structured JSON  -> CompanyMailAdapter（第二階段）

Adapter 是「格式差異的吸收層」。正式 JSON Schema 與 Mock Schema 不同時，
只修改這裡，不動 Service / State / Component。
"""

from .alert_parser import ParsedAlert, parse_alert_subject, strip_security_tag
from .company_adapter import CompanyMailAdapter
from .mock_adapter import MockMailAdapter

__all__ = [
    "CompanyMailAdapter",
    "MockMailAdapter",
    "ParsedAlert",
    "parse_alert_subject",
    "strip_security_tag",
]
