"""應用層設定。

這是整個系統唯一需要因「開發環境 / 公司環境」而修改的檔案。

第一階段（個人電腦）：DATA_MODE = "mock"
第二階段（公司電腦）：DATA_MODE = "real"

UI / Component / State 不會因為 DATA_MODE 不同而需要修改。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------
# Data Mode
# --------------------------------------------------------------------------
# "mock" -> MockMailRepository   （讀 app/mock_data/*.json）
# "real" -> RealMailRepository   （讀公司端 LLM 產生的結構化 JSON）
#
# 也可以用環境變數覆蓋，方便在不改 code 的情況下切換：
#   PowerShell:  $env:MAIL_DASHBOARD_DATA_MODE = "real"; reflex run
DATA_MODE: str = os.getenv("MAIL_DASHBOARD_DATA_MODE", "mock").strip().lower()


# --------------------------------------------------------------------------
# 路徑
# --------------------------------------------------------------------------
APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent

# Mock 階段的資料來源
MOCK_DATA_DIR: Path = APP_DIR / "mock_data"

def _find_dir(env_var: str, target_name: str, max_depth: int = 4) -> Optional[Path]:
    """找出某個資料夾的實際位置。

    優先看環境變數；沒設定就從專案根目錄往下找同名資料夾。

    這樣設計是為了「換一台電腦就能跑」：pipeline 的輸出目錄在個人電腦與
    公司電腦上幾乎不可能同名同路徑，寫死任何一個都會在移機時失效。
    """
    override = os.getenv(env_var, "").strip()
    if override:
        return Path(override)

    for depth in range(1, max_depth + 1):
        pattern = "/".join(["*"] * (depth - 1) + [target_name]) if depth > 1 else target_name
        for candidate in sorted(PROJECT_ROOT.glob(pattern)):
            if candidate.is_dir():
                return candidate
    return None


def _find_file(env_var: str, target_name: str, max_depth: int = 5) -> Optional[Path]:
    """同 _find_dir，但找的是檔案。"""
    override = os.getenv(env_var, "").strip()
    if override:
        return Path(override)

    for depth in range(1, max_depth + 1):
        pattern = "/".join(["*"] * (depth - 1) + [target_name]) if depth > 1 else target_name
        for candidate in sorted(PROJECT_ROOT.glob(pattern)):
            if candidate.is_file():
                return candidate
    return None


# 公司環境的資料來源：personal_assistant_v2 pipeline 的輸出根目錄。
# 結構為 <REAL_DATA_DIR>/<YYYY-MM-DD[-批次後綴]>/mails|summaries/...
#
# 自動尋找專案底下的 daily_reports 資料夾；找不到時退回 <專案>/real_data。
# 要指向專案外的位置（例如公司電腦上的網路磁碟）就設環境變數：
#   $env:MAIL_DASHBOARD_REAL_DATA_DIR = "D:\mail_pipeline\daily_reports"
REAL_DATA_DIR: Path = (
    _find_dir("MAIL_DASHBOARD_REAL_DATA_DIR", "daily_reports")
    or PROJECT_ROOT / "real_data"
)

# 郵件圖片 / 附件的對外 URL 前綴。
# Mock 階段檔案放在 assets/ 底下，由 Reflex 直接以靜態檔案提供。
ASSET_URL_PREFIX: str = os.getenv("MAIL_DASHBOARD_ASSET_PREFIX", "/")

# 真實郵件的內嵌圖片不在 assets/ 底下（在 REAL_DATA_DIR 裡），
# 因此由後端掛一個靜態路由提供，見 app/main.py。
REAL_ASSET_ROUTE: str = "/mail-assets"


# --------------------------------------------------------------------------
# Mock 專用設定（DATA_MODE = "real" 時完全不生效）
# --------------------------------------------------------------------------
# Mock JSON 內的日期是以這一天為基準寫死的。
MOCK_ANCHOR_DATE: str = "2026-08-09"

# 是否把 Mock 資料的日期平移到「執行當天」。
# 開啟後不論哪一天打開 Demo，「今日總覽」都有資料，不會因為過了 8/9 就變空白。
# 這是 Mock Repository 內部的行為，UI 完全不知道有這回事。
MOCK_SHIFT_DATES: bool = True


# --------------------------------------------------------------------------
# 介面設定
# --------------------------------------------------------------------------
APP_TITLE: str = "AI 郵件智慧決策助理"
APP_SHORT_TITLE: str = "AI Mail Decision"

# 開發階段在 Header 顯示 "MOCK DATA" 小 Badge；正式版自動關閉。
SHOW_MOCK_BADGE: bool = DATA_MODE == "mock"

# --------------------------------------------------------------------------
# 使用者身分
# --------------------------------------------------------------------------
# 身分不寫死在這裡，而是沿用公司 pipeline 已經設定好的 user_identity，
# 避免同一份資料要維護兩次（改了 pipeline 卻忘了改 Dashboard）。
#
# 讀取優先序（後者覆蓋前者）：
#   1. 下方的預設值（Mock 展示用的假身分）
#   2. personal_assistant_v2/alert_config.json 的 user_identity
#   3. 環境變數 MAIL_DASHBOARD_USER_NAME / _ROLE / _EMAIL
#
# 注意：alert_config.json 內同時存有密碼與 API Key，
# 這裡「只」讀 user_identity 與 priority_sender_keywords，其餘一律不碰。
# 自動尋找專案底下的 alert_config.json；移機後不需要改路徑。
COMPANY_CONFIG_PATH: Path = (
    _find_file("MAIL_DASHBOARD_COMPANY_CONFIG", "alert_config.json")
    or PROJECT_ROOT / "alert_config.json"
)

_DEFAULT_USER: dict[str, str] = {
    "name": "張協理",
    "email": "user@company.com",
    "role": "製造技術部",
    "initials": "張",
}


def _read_company_config() -> dict:
    """讀取公司 pipeline 的設定檔，失敗時回傳空 dict。

    設定檔不存在或格式壞掉都不應該讓 Dashboard 起不來。
    """
    try:
        import json

        with COMPANY_CONFIG_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _initials_of(name: str) -> str:
    """頭像文字：中文取姓，英文取首字母。"""
    clean = (name or "").strip()
    if not clean:
        return "?"
    first = clean[0]
    return first.upper() if first.isascii() and first.isalpha() else first


def _build_current_user() -> dict[str, str]:
    """組出 Header 要顯示的使用者身分。"""
    user = dict(_DEFAULT_USER)

    identity = _read_company_config().get("user_identity") or {}
    if isinstance(identity, dict):
        if identity.get("name"):
            user["name"] = str(identity["name"]).strip()
        if identity.get("email"):
            user["email"] = str(identity["email"]).strip()
        if identity.get("role_profile"):
            user["role"] = str(identity["role_profile"]).strip()

    # 環境變數優先權最高，方便不同人在同一台機器上切換。
    user["name"] = os.getenv("MAIL_DASHBOARD_USER_NAME", user["name"])
    user["role"] = os.getenv("MAIL_DASHBOARD_USER_ROLE", user["role"])
    user["email"] = os.getenv("MAIL_DASHBOARD_USER_EMAIL", user["email"])
    user["initials"] = _initials_of(user["name"])
    return user


CURRENT_USER: dict[str, str] = _build_current_user()


def _build_key_person_keywords() -> list[str]:
    """主管 / 關鍵窗口的比對關鍵字。

    同樣沿用公司 pipeline 的 priority_sender_keywords，
    環境變數 MAIL_DASHBOARD_KEY_PERSONS 可以再追加（逗號分隔）。
    """
    keywords = [
        str(k).strip()
        for k in (_read_company_config().get("priority_sender_keywords") or [])
        if str(k).strip()
    ]
    keywords += [
        k.strip()
        for k in os.getenv("MAIL_DASHBOARD_KEY_PERSONS", "").split(",")
        if k.strip()
    ]
    # 去重但保留順序
    seen: set[str] = set()
    return [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))]


KEY_PERSON_KEYWORDS: list[str] = _build_key_person_keywords()


# --------------------------------------------------------------------------
# AI 設定
# --------------------------------------------------------------------------
# 第一階段不呼叫任何 LLM API。AskAIService 走本機規則比對 Mock Data。
# 第二階段把這裡打開，並實作 services/ai_service.py 內的 LlmAskAIEngine。
AI_MODE: str = os.getenv("MAIL_DASHBOARD_AI_MODE", "mock").strip().lower()


def is_mock_mode() -> bool:
    """目前是否為 Mock 資料模式。"""
    return DATA_MODE == "mock"
