# AI 郵件智慧決策助理 — 系統架構

最後更新：2026-08-10

---

## 1. 這套系統是什麼

一個 Reflex（Python 全端框架）做的桌面版 Web Dashboard，把 Lotus Notes 的郵件
與 LLM 的分析結果整理成「今天要處理什麼」的決策畫面。

**它不取代 Lotus Notes**，也不負責收信、寄信或跑 LLM。它只負責「呈現」。
擷取與分析由另一套 pipeline（`personal_assistant_v2`）完成。

### 兩套系統的分工

```
┌─────────────────────────────────┐   ┌──────────────────────────────┐
│  personal_assistant_v2          │   │  本專案（Dashboard）           │
│  （擷取 + 分析，另一個 repo）      │   │                              │
│                                 │   │                              │
│  Lotus Notes                    │   │                              │
│    → Step A 擷取                 │   │                              │
│    → Step C Qwen 多模態摘要       │──▶│  讀取 JSON → 呈現              │
│    → Step D 產生日報              │   │                              │
│                                 │   │                              │
│  輸出：daily_reports/            │   │  不碰 Notes、不呼叫 LLM        │
└─────────────────────────────────┘   └──────────────────────────────┘
```

交界面就是 `daily_reports/` 這個資料夾。Dashboard 只讀它，不寫它。

---

## 2. 最重要的設計原則

**UI 與資料來源完全解耦。**

```
Component  →  State  →  Service  →  Repository  →  Adapter  →  JSON / API
   ▲                                     ▲
   │                                     │
只認得 Model                    只有這兩層知道資料從哪來
```

具體規則：

| 層 | 可以做什麼 | 不可以做什麼 |
|---|---|---|
| `components/` | 顯示傳進來的 Model | 讀檔、知道檔案路徑、知道 Notes/LLM 存在 |
| `pages/` | 組合 component | 同上 |
| `states/` | 存畫面狀態、呼叫 Service | 業務判斷（「什麼算重要」）、import repositories |
| `services/` | 業務邏輯：分類、篩選、統計 | 知道資料是 JSON 還是資料庫 |
| `repositories/` | 決定資料從哪讀 | 決定資料怎麼顯示 |
| `adapters/` | 吸收外部格式差異 | 業務判斷 |

**切換資料來源只要改一個環境變數**，UI 一行都不用動：

```powershell
$env:MAIL_DASHBOARD_DATA_MODE = "mock"   # 讀 app/mock_data/*.json（假資料，可離線展示）
$env:MAIL_DASHBOARD_DATA_MODE = "real"   # 讀 daily_reports/（公司 pipeline 的真實輸出）
```

---

## 3. 目錄結構

```
AI 郵件智慧決策助理/
├── rxconfig.py              Reflex 框架設定（port、主題、plugin）
├── ARCHITECTURE.md          本文件
│
├── app/
│   ├── config.py            ★ 唯一需要因環境調整的檔案
│   ├── theme.py             色彩 / 尺寸 token（元件不自己寫色碼）
│   ├── navigation.py        Sidebar 導覽定義
│   ├── main.py              進入點、路由、圖片靜態掛載
│   │
│   ├── models/              內部資料模型（系統的共同語言）
│   │   ├── mail.py          Mail / Sender / ContentBlock
│   │   ├── ai_analysis.py   AIAnalysis / TodoItem / KeyFact
│   │   ├── dashboard.py     KpiSummary / DailyBrief / SystemAlert
│   │   ├── attachment.py
│   │   ├── ask_ai.py
│   │   └── enums.py         MailCategory / Severity / NavKey / MailFilter
│   │
│   ├── repositories/        資料存取
│   │   ├── base_mail_repository.py    介面（合約）
│   │   ├── mock_mail_repository.py    Mock 實作
│   │   ├── real_mail_repository.py    公司 pipeline 實作
│   │   └── adapters/
│   │       ├── mock_adapter.py        Mock JSON → Model
│   │       ├── company_adapter.py     公司 JSON → Model
│   │       └── alert_parser.py        告警主旨解析
│   │
│   ├── services/            業務邏輯
│   │   ├── mail_service.py        分類 / 搜尋 / 篩選 / 統計
│   │   ├── dashboard_service.py   KPI 計算
│   │   └── ai_service.py          Ask AI（引擎可抽換）
│   │
│   ├── states/app_state.py  全域畫面狀態
│   ├── components/          14 個 UI 元件
│   ├── pages/               7 個頁面
│   └── mock_data/           Mock 用的假資料
│
├── assets/mock/images/      Mock 郵件的圖片
└── AI_Mail_system-main/     ⚠ 公司 pipeline 的複本與真實郵件資料（見第 7 節）
```

---

## 4. 資料流

### Mock 模式

```
app/mock_data/*.json  →  MockMailAdapter  →  MockMailRepository  →  Service  →  State  →  UI
```

Mock JSON 的日期錨定在 `MOCK_ANCHOR_DATE`，載入時會整體平移到執行當天，
所以任何一天打開 Demo「今日總覽」都有資料。這是 MockRepository 的內部行為，上層不知情。

### Real 模式

```
daily_reports/YYYY-MM-DD[-批次]/
    mails/mail_NNNN/mail.json          ← Step A 產出
    mails/mail_NNNN/body_image_*.gif   ← 郵件內嵌圖片
    summaries/mail_NNNN_summary.json   ← Step C 產出
    daily_digest.md                    ← Step D 產出
              │
              ▼
    CompanyMailAdapter（吸收格式差異）
              │
              ▼
    RealMailRepository（依日期分組、聚合告警、合成今日重點）
              │
              ▼
    Service → State → UI
```

同一天可以有多個批次資料夾（`2026-08-07` 與 `2026-08-07-MAIL41_TO_MAIL64`），
Repository 依資料夾名稱開頭的 `YYYY-MM-DD` 自動歸為同一天並合併。

---

## 5. 公司 Schema 與內部 Model 的對應

**這是移機後最可能需要調整的地方**——如果 pipeline 的輸出格式改了，只改
`adapters/company_adapter.py`，不要動其他層。

### mail.json → Mail

| 內部 Model | 公司欄位 | 處理 |
|---|---|---|
| `mail_id` | `mail_id` | 直接對應 |
| `subject` | `subject` | 移除結尾的 `(Security C)` 標記 |
| `sender` | `from`（純字串，4 種格式） | `_parse_sender()` 解析 |
| `sent_at` | `date`（只有日期沒有時間） | 補 00:00；`time_label` 留空 |
| `content_blocks` | `blocks`（image 用 `path`+`format`） | 改名 + 組圖片 URL |
| `to` / `cc` | `to` / `cc` | 直接對應（值可能是群組名而非 email） |
| `is_read` / `attachments` | 無 | 一律當未讀 / 空清單 |

`from` 實際有四種格式，解析器都要處理（以下為示意值）：

```
"Alert System" <alert-system@example.com>
Alert System <alert-system@example.com>
CN=Some User/OU=DEPT/O=ORG           ← 沒有 email
Some User/DEPT/ORG                   ← 沒有 email
```

### summary.json → AIAnalysis

| 內部 Model | 公司欄位 | 處理 |
|---|---|---|
| `category` | `category`（7 種值域） | `_CATEGORY_MAP` 對照 |
| `importance`（1–5） | `priority`（high/medium/low） | 三級轉五級，見下 |
| `todos` | `action_items` | 改名 |
| `key_points` | `key_points` | 直接對應（純字串陣列） |
| `key_facts` | 無 | 公司端沒有 label/value 配對 |
| `action_required` | `reply_needed` + `category` | 綜合判定 |
| `addressed_to` | `addressed_to_me` | direct/cc/broadcast |
| `deadline` | `deadline` | Step C 已保證是 `YYYY-MM-DD` 或空字串 |
| `recommendations` | `recommendations` | 直接對應 |
| `reply_draft` | `reply_draft` | 直接對應 |

**三級轉五級的公式**（在 `_to_importance()`）：

```
基礎分   high=5 / medium=3 / low=1
  +1     category 是 urgent 或 action_required
  +1     addressed_to_me == "direct"
上限 5
```

單看 `priority` 會壓縮太多資訊（實際資料只有 low/medium，全部落在 1 或 3 星，
「重要郵件」永遠是 0 封），所以納入另外兩個公司端已經判好的訊號。

### machine_alert → SystemAlert

公司資料**沒有獨立的告警檔**，事件是從 `category == "machine_alert"` 的郵件推導的。

這類告警信的 `blocks` 通常是空的（Step A 抓不到本文），但主旨是固定格式，
資訊全在主旨裡，由 `alert_parser.py` 取出：

```
【汙染因子超標通知】X1 關鍵機台 X1_TOOL_03 - PSN X1_TOOL_03#P1 狀態 OOS
                  ^^  ^^^^^^^^  ^^^^^^^^^^        ^^^^^^^^^^^^^  ^^^
                  區域   關鍵性      機台              PSN 點位     狀態
```
（機台代號為示意值）

同類告警依 `alert_key` 聚合（實測 52 封 → 31 組），關鍵機台自動升為「嚴重」。

---

## 6. 移到公司電腦要做什麼

### 6.1 一定要做

**1. 建立虛擬環境並安裝套件**

```powershell
cd "<專案路徑>"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install reflex
```

`.venv/` 不要複製過去，一定要重建（裡面有絕對路徑）。

**2. 指定資料來源模式**

```powershell
$env:MAIL_DASHBOARD_DATA_MODE = "real"
```

要永久生效：

```powershell
[Environment]::SetEnvironmentVariable("MAIL_DASHBOARD_DATA_MODE", "real", "User")
```

**3. 確認 pipeline 輸出目錄找得到**

`config.py` 會自動從專案根目錄往下找名為 `daily_reports` 的資料夾（最多 4 層）。
如果 pipeline 的輸出在專案外（例如網路磁碟或 D 槽），要明確指定：

```powershell
$env:MAIL_DASHBOARD_REAL_DATA_DIR = "D:\mail_pipeline\daily_reports"
```

**4. 確認身分設定檔找得到**

同樣會自動找 `alert_config.json`（最多 5 層）。找不到就會用預設的假身分（張協理）。
要明確指定：

```powershell
$env:MAIL_DASHBOARD_COMPANY_CONFIG = "D:\mail_pipeline\personal_assistant_v2\alert_config.json"
```

**5. 檢查 port 沒被佔用**

`rxconfig.py` 用 3000（前端）/ 8000（後端）。公司電腦若已被佔用：

```powershell
reflex run --frontend-port 3001 --backend-port 8001
```

### 6.2 驗證有沒有接上

啟動後開 `/settings`，那一頁刻意把所有路徑攤開來顯示：

- **DATA_MODE** 是 `real` 不是 `mock`
- **狀態** 顯示 `OK — <日期> 共 N 封郵件`，不是「找不到目錄」
- **Mock 資料目錄 / 公司資料目錄** 兩個路徑是否指到對的地方
- **使用者身分** 是否顯示你的名字而不是「張協理」

### 6.3 環境變數總表

| 變數 | 用途 | 不設的話 |
|---|---|---|
| `MAIL_DASHBOARD_DATA_MODE` | `mock` / `real` | `mock` |
| `MAIL_DASHBOARD_REAL_DATA_DIR` | pipeline 輸出目錄 | 自動找 `daily_reports` |
| `MAIL_DASHBOARD_COMPANY_CONFIG` | 身分設定檔 | 自動找 `alert_config.json` |
| `MAIL_DASHBOARD_USER_NAME` / `_ROLE` / `_EMAIL` | 覆蓋顯示的身分 | 讀設定檔 |
| `MAIL_DASHBOARD_KEY_PERSONS` | 主管名單（逗號分隔，會疊加） | 讀設定檔的 `priority_sender_keywords` |
| `MAIL_DASHBOARD_AI_MODE` | `mock` / `llm` | `mock` |

**不需要改任何 `.py` 檔**。若發現非改不可，代表有東西寫死了，應該改成環境變數。

---

## 7. 注意事項

### pipeline 的輸出目錄含機敏資料

`daily_reports/` 是真實郵件（含公司資料分級標記、同事姓名、內部路徑），
pipeline 的設定檔則含連線憑證。

- 這個專案若要納入版控，`.gitignore` 必須排除它們（已預先設定）
- 不要上傳到任何公開位置
- 移機時**不需要複製**——公司電腦上 pipeline 本來就會產出

### Reflex 的兩個地雷

1. **dataclass 欄位不可與 Var 方法同名**（`items` / `to` / `keys` / `values`）。
   `ContentBlock` 的清單欄位因此叫 `list_items` 而不是 `items`。
2. **`rx.icon(tag)` 的 tag 必須是編譯期常數**，不能傳 Var。
   要依狀態換圖示就對整顆元件做 `rx.cond`。

兩者的錯誤訊息都是 `TypeError: Cannot pass a Var to a built-in function`，
完全看不出真因。用以下指令可以在幾秒內逐頁抓出來：

```powershell
python -c "import app.main as m; [m.app._compile_page(r, save_page=False) for r in m.app._unevaluated_pages]"
```

### 目前已知的限制

| 項目 | 說明 |
|---|---|
| 郵件沒有時間 | pipeline 只輸出 `date`，Mail List 不顯示時分 |
| 沒有已讀狀態 | Notes 的已讀旗標沒匯出，一律當未讀 |
| 沒有附件 | Step A 不擷取附件，只有內嵌圖片 |
| 告警信本文是空的 | 資訊靠主旨解析補；4 種主旨格式外的會顯示「—」 |
| 告警規則有誤判 | HR 公告等會被歸成 `machine_alert`（pipeline 側的規則問題） |
| 不實作寄信 | 「建立 Draft」只在畫面上標記，不會真的寄出 |
