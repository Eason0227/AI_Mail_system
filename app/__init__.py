"""AI 郵件智慧決策助理。

Layer 結構（資料一律單向往上流動）::

    Repository  ->  Service  ->  State  ->  UI Component

UI 不知道資料來自 Mock JSON、Lotus Notes、公司 API 或 SQLite。
切換資料來源只需要修改 app/config.py 的 DATA_MODE。
"""
