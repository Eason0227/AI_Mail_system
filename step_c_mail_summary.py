"""
Step C：單封信多模態摘要與分類

- 直接讀取 Step A 產生的 mail.json（文字 + 圖片）
- 用同一個多模態模型辨識圖片、分類並生成摘要
- 輸出 summaries/mail_NNNN_summary.json

可單獨執行：python step_c_mail_summary.py
"""

import base64
import io
import json
import re
from datetime import date
from pathlib import Path

import requests

from config import (
    CONFIG,
    BASE_OUTPUT_DIR,
    LLM_API_URL,
    LLM_API_KEY,
    LLM_MODEL_NAME,
)


# ============================================================
# 設定區（皆由 config.py / alert_config.json 提供，可自訂）
#   - BASE_OUTPUT_DIR / LLM_* ：見 config.py
#   - 告警辨識三層防線：
#       1) 使用者自訂寄件者/主旨關鍵字（alert_config.json）
#       2) 通用機器人寄件者特徵自動偵測（no-reply / notification…）
#       3) LLM 兜底：規則沒命中時，由 LLM 判定 category=machine_alert
# ============================================================

# 集中設定即為告警設定來源（config 已合併預設值 + alert_config.json）
ALERT_CONFIG = CONFIG


def is_machine_alert(sender: str, subject: str, cfg: dict | None = None) -> bool:
    """
    依三層規則判斷是否為系統自動告警：
      1) 使用者自訂寄件者關鍵字
      2) 使用者自訂主旨關鍵字
      3) 通用機器人寄件者特徵（可關閉）
    """
    cfg = cfg or ALERT_CONFIG
    s = (sender or "").lower()
    subj = (subject or "").lower()

    # (1) 自訂寄件者關鍵字
    if any(kw.lower() in s for kw in cfg.get("machine_sender_keywords", [])):
        return True

    # (2) 自訂主旨關鍵字
    if any(kw.lower() in subj for kw in cfg.get("machine_subject_keywords", [])):
        return True

    # (3) 通用機器人寄件者特徵（不管系統名稱叫什麼）
    if cfg.get("enable_auto_detect", True):
        if any(p.lower() in s for p in cfg.get("auto_sender_patterns", [])):
            return True

    return False


def extract_alert_fields(subject: str) -> dict:
    """
    從主旨萃取聚合用欄位（alert_type / alert_key / machine）。
    規則路徑與 LLM 兜底路徑共用，確保 Step D 都能聚合。
    """
    subj = subject or ""

    if "斷線" in subj or "離線" in subj:
        alert_type = "裝置斷線/離線"
    elif "超標" in subj or "OOS" in subj.upper() or "OOC" in subj.upper():
        alert_type = "汙染因子超標"
    elif "機台異常" in subj or "機差" in subj:
        alert_type = "機台異常"
    elif "daily report" in subj.lower() or "派報" in subj:
        alert_type = "自動派報"
    else:
        alert_type = "其他系統告警"

    # 機台/裝置代號（如 B1_COAT_01、ASES2-2864-C01、ASE07-2800-7I21）
    m = re.search(r"[A-Z0-9]{2,}[_\-][A-Z0-9_\-]+", subj)
    machine = m.group(0) if m else "N/A"

    # 聚合鍵：去數字後的主旨骨架，讓「16台/6台/5台」歸為同群
    subj_skeleton = re.sub(r"\d+", "#", subj)
    subj_skeleton = re.sub(r"\s+", " ", subj_skeleton).strip()
    alert_key = f"{alert_type}｜{subj_skeleton}"

    return {"alert_type": alert_type, "alert_key": alert_key, "machine": machine}


#: 所有摘要都要有的欄位與其空值。
#: 下游（Step D、Dashboard）可以直接取用，不必逐一判斷欄位存不存在。
SUMMARY_DEFAULTS: dict = {
    "category":        "fyi",
    "priority":        "low",
    "addressed_to_me": "unknown",
    "summary":         "",
    "deadline":        "",
    "action_items":    [],
    "key_points":      [],
    "recommendations": [],
    "reply_draft":     "",
    "reply_needed":    False,
}


def normalize_summary(summary: dict) -> dict:
    """補齊缺漏欄位，確保每份摘要的 Schema 一致。

    LLM 偶爾會省略空欄位，搶救路徑也只會拿到部分欄位。
    在這裡統一補上空值，下游就不需要到處寫 .get(key, 預設值)。
    """
    if not isinstance(summary, dict):
        return summary
    # 模型失敗時保留原始錯誤結構，不要用預設值蓋掉問題。
    if "error" in summary or "raw_llm" in summary:
        return summary
    for key, empty in SUMMARY_DEFAULTS.items():
        if summary.get(key) is None or key not in summary:
            summary[key] = list(empty) if isinstance(empty, list) else empty
    return summary


#: 模型常見的「沒有截止日」寫法，一律視為空值。
_DEADLINE_NULLS = {"無", "未提及", "未提供", "none", "null", "n/a", "na", "-", "無明確截止日期"}


def validate_deadline(summary: dict, mail_date: str) -> dict:
    """把 deadline 正規化成 YYYY-MM-DD，擋掉明顯不合理的值。

    模型即使被要求只輸出日期，仍可能回「無」、「2026/08/12」或
    離信件日期十年遠的幻覺日期。這裡統一清洗，讓下游可以無條件信任這個欄位。
    """
    if not isinstance(summary, dict):
        return summary

    raw = str(summary.get("deadline", "") or "").strip()
    if not raw or raw.lower() in _DEADLINE_NULLS:
        summary["deadline"] = ""
        return summary

    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", raw)
    if not m:
        summary["deadline"] = ""
        return summary

    try:
        parsed = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        summary["deadline"] = ""
        return summary

    # 與信件日期比對，過去太久或未來太遠都視為幻覺。
    base = None
    bm = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(mail_date or ""))
    if bm:
        try:
            base = date(int(bm.group(1)), int(bm.group(2)), int(bm.group(3)))
        except ValueError:
            base = None

    if base is not None:
        delta = (parsed - base).days
        if delta < -30 or delta > 365:
            print(f"    [警告] deadline {parsed} 與信件日期 {base} 相距過遠，已捨棄")
            summary["deadline"] = ""
            return summary

    summary["deadline"] = parsed.isoformat()
    return summary


def build_machine_alert_summary(mail_id: str, subject: str, sender: str) -> dict:
    """系統告警的輕量摘要（不呼叫 LLM），主旨即摘要並帶聚合欄位。"""
    fields = extract_alert_fields(subject)
    return normalize_summary({
        "mail_id":      mail_id,
        "subject":      subject,
        "from":         sender,
        "category":     "machine_alert",
        "priority":     "low",
        "summary":      subject,          # 系統告警主旨即摘要
        "reply_needed": False,
        **fields,                         # alert_type / alert_key / machine
    })


LLM_SYSTEM_PROMPT = """
你是一位專業的個人信件助理，服務對象是「本人（收件助理的使用者）」。
請直接閱讀一封信件的完整文字與圖片，以結構化 JSON 格式回應，
幫助本人快速了解信件重點與行動項目。

【圖片判讀】
- 圖片可能是郵件正文中的表格、圖表、截圖、照片、流程圖、Logo 或簽名。
- 請把圖片中的重要數據、異常、截止日期及待辦納入摘要與分類。
- 裝飾圖片、Logo、分隔線及簽名圖示不需描述，也不可因此捏造待辦。

【收件人身分判斷（影響 reply_needed 很重要）】
- 我會在使用者訊息開頭提供「本人身分」（姓名/別名/email）與這封信的 To / Cc 名單。
- 若本人出現在 To（直接收件人）→ 這封信通常要本人處理或回覆，reply_needed 傾向 true。
- 若本人「只」出現在 Cc、或屬於大量群發/部門群組、或本人不在收件名單中
  → 本人多半只是被知會，reply_needed 傾向 false（除非內文明確點名要求本人回覆/提供資料）。
- 若無法判斷收件人（名單空白），則依內文語氣與是否直接點名本人來判斷。

【分類規則】
- urgent          = 今日或明日前必須「由本人」行動、含「緊急」「URGENT」「ASAP」字樣、高層直接指示本人
- action_required = 需要本人回覆或跟進，但不緊急（無明確截止今日）
- meeting         = 會議邀請、行事曆通知、場地預約
- report          = 定期報告、數據摘要（如日報、週報、月報）
- fyi             = 知悉即可，不需本人採取行動的通知/公告（含只被 Cc 的群發信）
- machine_alert   = 系統/機台自動發出的告警或監控通知（如設備異常、超標、斷線、離線、
                    自動派報、no-reply 系統信）。通常主旨格式固定、由自動系統寄出、
                    大量重複、不需個別回覆。
- junk            = 廣告、行銷、垃圾郵件

【優先順序】urgent > action_required > meeting > report > machine_alert > fyi > junk
（判斷準則：若這封信是「自動系統」寄出、且內容為監控/告警/派報性質，一律歸 machine_alert）
（若本人只是被 Cc 的知會對象且無需行動，即使內容重要也應歸 fyi，並把 reply_needed 設 false）

【截止日期判斷（deadline）】
- 只有信件內容「明確寫出」的截止日期才可以填，絕不可推測或自行設定。
- 使用者訊息開頭會提供「信件日期」。相對日期一律依信件日期換算成絕對日期，例如
  信件日期為 2026-08-07 時：「本週五」→ 2026-08-08、「下週三」→ 2026-08-12、「月底前」→ 2026-08-31。
- 一封信有多個日期時，取「本人需要完成動作」的那一個；純粹敘述過去事件的日期不算。
- 沒有明確截止日期時填空字串 ""，不要填「無」或「未提及」。

【建議處置（recommendations）】
- 站在本人的立場，列出 2~4 項具體、可立即執行的下一步。
- 只能根據信件實際內容提出；不可捏造不存在的系統、報表或聯絡人。
- 每項 30 字以內，用動詞開頭，例如「確認 B1_OVEN_03 近三日 Particle 趨勢」。
- 分類為 fyi / junk / machine_alert 時填 []。

【回覆草稿（reply_draft）】
- 只有 reply_needed 為 true 時才產生；false 時填空字串 ""。
- 繁體中文商務書信語氣，開頭稱謂寄件者，結尾署名一律寫「本人」（後續由使用者自行替換）。
- 150 字以內，只回應信件實際提到的事項，不可代替本人承諾信中沒有的時程或結論。
- 需要換行時使用 \\n，不可直接輸出實體換行。

【輸出 JSON Schema】
{
  "mail_id": "string（如 mail_0001）",
  "subject": "string",
  "from": "string",
  "category": "urgent | action_required | meeting | report | machine_alert | fyi | junk",
  "priority": "high | medium | low",
  "addressed_to_me": "direct | cc | broadcast | unknown（本人為直接收件人/僅被副本/群發/無法判斷）",
  "summary": "string（50 字以內，說明這封信的核心內容）",
  "deadline": "YYYY-MM-DD 或空字串（僅限信中明確寫出的截止日期）",
  "action_items": ["需要本人做什麼（若有截止日期請附上）"],
  "key_points": ["重點摘要 1", "重點摘要 2"],
  "recommendations": ["建議處置 1", "建議處置 2"],
  "reply_draft": "string（reply_needed 為 false 時填空字串）",
  "reply_needed": true 或 false
}

【規則】
1. summary 不得超過 50 字
2. 無內容的欄位一律填空值：陣列填 []、字串填 ""，不要省略欄位，也不要填「無」
3. 所有欄位以繁體中文填寫（mail_id / category / priority / addressed_to_me / deadline 除外）
4. 絕不捏造信件未提及的內容；deadline 與 recommendations 尤其不可自行發明
5. 只輸出 JSON，不要任何說明文字
6. 字串值內「不得」出現半形雙引號 " ；若需引用檔名或名稱，一律改用中文全形引號「」，以免破壞 JSON 格式
"""


# ============================================================
# LLM 摘要
# ============================================================

def build_identity_block(cfg: dict | None = None) -> str:
    """組出「本人身分」說明，供 LLM 判斷收件人關係。"""
    cfg = cfg or ALERT_CONFIG
    ident = cfg.get("user_identity", {}) or {}
    name = ident.get("name", "").strip()
    role = ident.get("role_profile", "").strip()
    aliases = [a for a in ident.get("aliases", []) if a]
    email = ident.get("email", "").strip()

    if not (name or role or aliases or email):
        return "（未設定本人身分，請依內文判斷收件人關係）"

    parts = []
    if name:
        parts.append(f"姓名：{name}")
    if role:
        parts.append(f"角色定位：{role}")
    if aliases:
        parts.append(f"別名：{'、'.join(aliases)}")
    if email:
        parts.append(f"email：{email}")
    return "；".join(parts)


def is_priority_sender(sender: str, cfg: dict | None = None) -> bool:
    """寄件者命中優先名單時，強制把 priority 提升為 high。"""
    cfg = cfg or ALERT_CONFIG
    s = (sender or "").lower()
    patterns = cfg.get("priority_sender_keywords", []) or []
    return any((p or "").strip() and (p or "").lower() in s for p in patterns)


def apply_priority_sender_override(summary: dict, sender: str, cfg: dict | None = None) -> dict:
    """若寄件者在優先名單，覆蓋摘要 priority 並加註重點。"""
    if not isinstance(summary, dict):
        return summary
    if not is_priority_sender(sender, cfg):
        return summary

    summary["priority"] = "high"
    note = "寄件者命中優先處理名單"
    key_points = summary.get("key_points")
    if isinstance(key_points, list) and note not in key_points:
        key_points.insert(0, note)
    return summary


def is_signature_image(image_path: Path) -> bool:
    """略過小型 Logo、簽名圖示與分隔線，避免浪費多模態 token。"""
    try:
        if image_path.stat().st_size < 20 * 1024:
            return True
        from PIL import Image  # type: ignore[reportMissingImports]
        with Image.open(image_path) as img:
            width, height = img.size
            return width * height < 6000 or height < 80
    except Exception:
        return False


def image_to_data_url(image_path: Path) -> str:
    """讀取圖片並統一轉為 PNG data URL，供 OpenAI 相容多模態 API 使用。"""
    raw = image_path.read_bytes()
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(image_path.suffix.lower(), "application/octet-stream")
    try:
        from PIL import Image  # type: ignore[reportMissingImports]
        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            raw = buffer.getvalue()
            mime_type = "image/png"
    except Exception:
        pass
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_multimodal_content(
    mail_id: str,
    subject: str,
    sender: str,
    to_list: list[str],
    cc_list: list[str],
    blocks: list[dict],
    mail_dir: Path,
    mail_date: str = "",
) -> tuple[list[dict], int, int]:
    """依原始順序組合文字與圖片，回傳 API content、送出及略過圖片數。"""
    identity_block = build_identity_block()
    to_str = "、".join(to_list) if to_list else "（無 / 未擷取）"
    cc_str = "、".join(cc_list) if cc_list else "（無 / 未擷取）"
    # 信件日期是 deadline 欄位的換算基準（「下週三」要換成絕對日期）。
    date_str = mail_date or "（未提供，遇到相對日期時 deadline 請留空）"
    content: list[dict] = [{
        "type": "text",
        "text": (
            f"【本人身分】{identity_block}\n"
            f"【信件日期】{date_str}\n"
            f"【這封信的 To（直接收件人）】{to_str}\n"
            f"【這封信的 Cc（副本）】{cc_str}\n\n"
            f"mail_id: {mail_id}\nsubject: {subject}\nfrom: {sender}\n\n"
            "===== 信件完整內容（文字與圖片依原始順序排列） ====="
        ),
    }]
    sent_images = 0
    skipped_images = 0

    for block in blocks:
        if block.get("type") == "text":
            text = (block.get("content") or "").strip()
            if text:
                content.append({"type": "text", "text": text})
            continue
        if block.get("type") != "image":
            continue

        image_path = mail_dir / (block.get("path") or "")
        if not image_path.is_file() or is_signature_image(image_path):
            skipped_images += 1
            continue
        content.append({
            "type": "image_url",
            "image_url": {"url": image_to_data_url(image_path)},
        })
        sent_images += 1

    return content, sent_images, skipped_images


def summarize_mail(
    mail_id: str,
    subject: str,
    sender: str,
    blocks: list[dict],
    mail_dir: Path,
    to_list: list[str] | None = None,
    cc_list: list[str] | None = None,
    mail_date: str = "",
) -> tuple[dict, int, int]:
    """把整封信的文字與圖片一次送多模態模型，回傳摘要及圖片統計。"""
    sess = requests.Session()
    sess.trust_env = False  # 禁止使用系統 proxy

    user_content, sent_images, skipped_images = build_multimodal_content(
        mail_id, subject, sender, to_list or [], cc_list or [], blocks, mail_dir,
        mail_date,
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }

    resp = sess.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    response_content = resp.json()["choices"][0]["message"]["content"].strip()

    # 去除 LLM 可能包覆的 code fence
    if response_content.startswith("```"):
        response_content = response_content.split("\n", 1)[-1]
    if response_content.endswith("```"):
        response_content = response_content.rsplit("\n", 1)[0]

    cleaned = response_content.strip()
    try:
        return json.loads(cleaned), sent_images, skipped_images
    except json.JSONDecodeError:
        # LLM 常見錯誤：字串值內含未跳脫的半形雙引號，導致 JSON 破損。
        # 先嘗試用已知 schema 正則搶救關鍵欄位，讓 digest 至少能正確分類。
        salvaged = salvage_summary(cleaned)
        if salvaged:
            salvaged.setdefault("mail_id", mail_id)
            salvaged.setdefault("subject", subject)
            salvaged.setdefault("from", sender)
            return salvaged, sent_images, skipped_images
        # 完全無法搶救時保留原始文字，方便人工確認
        return (
            {"mail_id": mail_id, "subject": subject, "from": sender, "raw_llm": response_content},
            sent_images,
            skipped_images,
        )


def salvage_summary(text: str) -> dict:
    """JSON 解析失敗時，用正則逐欄位搶救可用資訊。"""
    result: dict = {}

    # 單值字串/布林欄位
    for key in (
        "mail_id", "subject", "from", "category", "priority",
        "addressed_to_me", "summary", "deadline", "reply_draft",
    ):
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if m:
            result[key] = m.group(1).replace('\\"', '"').replace("\\n", "\n")

    m = re.search(r'"reply_needed"\s*:\s*(true|false)', text)
    if m:
        result["reply_needed"] = (m.group(1) == "true")

    # 陣列欄位：抓取 [ ... ] 內的字串項目（容忍內部未跳脫引號的破損）
    for key in ("action_items", "key_points", "recommendations"):
        m = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if m:
            items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
            result[key] = [it.replace('\\"', '"').replace("\\n", "\n") for it in items]

    # 至少要有 category 才算搶救成功（digest 靠它分組）
    return result if result.get("category") else {}


# ============================================================
# 主流程
# ============================================================

def main(today_str: str | None = None) -> None:
    if today_str is None:
        today_str = date.today().strftime("%Y-%m-%d")

    mails_dir     = BASE_OUTPUT_DIR / today_str / "mails"
    summaries_dir = BASE_OUTPUT_DIR / today_str / "summaries"

    if not mails_dir.exists():
        print(f"[錯誤] 找不到 mails 目錄，請先執行 Step A: {mails_dir}")
        return

    summaries_dir.mkdir(parents=True, exist_ok=True)
    mail_dirs = sorted([d for d in mails_dir.iterdir() if d.is_dir()])
    print(f"[Step C] 共 {len(mail_dirs)} 封信待多模態摘要（今日：{today_str}）")

    for mail_dir in mail_dirs:
        mail_path = mail_dir / "mail.json"
        if not mail_path.exists():
            print(f"  [略過] 找不到 mail.json: {mail_dir}")
            continue

        try:
            mail = json.loads(mail_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [略過] 無法讀取 {mail_path}: {e}")
            continue

        mail_id = mail.get("mail_id", mail_dir.name)
        subject = mail.get("subject", "")
        sender = mail.get("from", "")
        to_list = mail.get("to", []) or []
        cc_list = mail.get("cc", []) or []
        blocks = mail.get("blocks", []) or []

        print(f"\n  多模態摘要 {mail_id}: {subject[:70]}")

        # 系統自動告警：規則分類，不送 LLM（省成本、避免淹沒真人信件）
        if is_machine_alert(sender, subject):
            summary = build_machine_alert_summary(mail_id, subject, sender)
            summary = apply_priority_sender_override(summary, sender)
            out_file = summaries_dir / f"{mail_id}_summary.json"
            out_file.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    → [machine_alert / {summary['alert_type']}]（規則分類，未送 LLM）")
            continue

        try:
            summary, sent_images, skipped_images = summarize_mail(
                mail_id, subject, sender, blocks, mail_dir, to_list, cc_list,
                mail.get("date", ""),
            )
            print(f"    → 圖片送出 {sent_images} 張，略過 {skipped_images} 張")
        except Exception as e:
            print(f"    [警告] 多模態模型失敗: {e}")
            summary = {"mail_id": mail_id, "subject": subject, "from": sender, "error": str(e)}

        # 第 3 層兜底：LLM 自行判定為系統告警時，補上聚合欄位供 Step D 使用
        if isinstance(summary, dict) and summary.get("category") == "machine_alert":
            summary.setdefault("priority", "low")
            summary.setdefault("reply_needed", False)
            for k, v in extract_alert_fields(subject).items():
                summary.setdefault(k, v)

        summary = normalize_summary(summary)
        summary = validate_deadline(summary, mail.get("date", ""))
        summary = apply_priority_sender_override(summary, sender)

        out_file = summaries_dir / f"{mail_id}_summary.json"
        out_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        cat = summary.get("category", "?")
        pri = summary.get("priority", "?")
        print(f"    → [{cat} / {pri}] {out_file.name}")

    print(f"\n[Step C] 完成：摘要存至 {summaries_dir}")


if __name__ == "__main__":
    main()
