# 🌤 Weather Telegram Notifier

自動抓取天氣預報，並透過 Telegram Bot 定時推送到你的手機。

## 功能

- ✅ 每日自動推送天氣預報（預設早上 7:00）
- ✅ 支援兩大資料源：
  - **Open-Meteo**（免費、免 API Key、全球覆蓋）← 預設
  - **中央氣象署 CWB 開放資料 API**（臺灣地區資料更詳細）
- ✅ 自動 Failover：Open-Meteo 失敗自動切換 CWB 備援
- ✅ Config-driven 架構：修改 `config.yaml` 即可調整設定
- ✅ 天氣資訊包含：氣溫（最高/最低）、體感溫度、降雨機率、濕度、風速風向、紫外線指數
- ✅ 支援手動觸發（GitHub UI 一键執行）
- ✅ 可自訂城市與資料源

## 快速開始

### 1. 建立 Telegram Bot

1. 在 Telegram 中搜尋 [@BotFather](https://t.me/BotFather)
2. 輸入 `/newbot` 並依指示建立新 Bot
3. 建立成功後，**保存 Bot Token**（格式如 `123456:ABC-DEF1234`）
4. 搜尋你的 Bot 並點擊「Start」啟用
5. 獲取你的 Chat ID：
   - 傳送任意訊息到你的 Bot
   - 開啟瀏覽器前往：`https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - 找到 `"chat":{"id":123456789}` 的值

### 2. Fork / Clone 此專案

```bash
git clone <your-repo-url>
cd weather_telegram_notifier
```

### 3. 設定設定檔

編輯 `config.yaml`（或複製為自訂路徑）：

```yaml
users:
  - name: "Tony"
    city: "臺北市"
    detail_level: full
    sources:
      - name: openmeteo
        priority: 1
      - name: cwb
        priority: 2
        api_key: ${CWB_API_KEY}
    notifiers:
      - name: telegram
        bot_token: ${TELEGRAM_BOT_TOKEN}
        chat_id: ${TELEGRAM_CHAT_ID}
```

環境變數 `${TELEGRAM_BOT_TOKEN}`, `${TELEGRAM_CHAT_ID}`, `${CWB_API_KEY}`
會在執行時自動從環境變數代換。

### 4. 設定 GitHub Secrets

在 GitHub Repo → **Settings → Secrets and variables → Actions** 新增：

| Secret | 說明 | 必要 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（從 @BotFather 取得） | ✅ |
| `TELEGRAM_CHAT_ID` | 接收通知的 Chat ID | ✅ |
| `CWB_API_KEY` | CWB API Key（僅使用 CWB source 時需要） | ❌ |

### 5. 啟用 GitHub Actions

Push 到 GitHub 後，Workflow 會自動啟用。
- 預設排程：**每日 UTC 23:00（台灣時間 07:00）**
- 也可在 GitHub → Actions → **Weather Forecast Notifier** → **Run workflow** 手動執行

## 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Dry-run（僅顯示，不發送）
python -m src.main --dry-run

# 執行並發送
python -m src.main

# 使用自訂設定檔
python -m src.main --config /path/to/config.yaml

# 覆蓋城市
python -m src.main --location 高雄市

# 覆蓋詳細程度
python -m src.main --detail basic
```

## 自訂設定

### `config.yaml` 欄位說明

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `users[].name` | 使用者名稱（僅供辨識） | - |
| `users[].city` | 城市名稱（如「臺北市」） | 臺北市 |
| `users[].detail_level` | 詳細程度：`basic` / `standard` / `full` | `full` |
| `users[].sources[].name` | 資料源名稱：`openmeteo` / `cwb` | - |
| `users[].sources[].priority` | 優先順序（數字越小越優先） | - |
| `users[].sources[].api_key` | API Key（可用 `${ENV_VAR}`） | - |
| `users[].notifiers[].name` | 通知頻道：`telegram` | - |
| `users[].notifiers[].bot_token` | Telegram Bot Token | `${TELEGRAM_BOT_TOKEN}` |
| `users[].notifiers[].chat_id` | Telegram Chat ID | `${TELEGRAM_CHAT_ID}` |

### 自訂 config 路徑

可透過環境變數 `CONFIG_PATH` 或 `--config` 參數指定：

```bash
export CONFIG_PATH=/etc/weather/config.yaml
python -m src.main
```

### Failover 行為

系統會依照 `priority` 順序嘗試資料源：
1. 第一個成功就停止
2. 若全部失敗，發送錯誤通知

## 專案結構

```
weather_telegram_notifier/
├── .github/workflows/
│   └── weather_forecast.yml    # GitHub Actions 排程
├── config.yaml                 # 設定檔（Config-driven）
├── src/
│   ├── __init__.py
│   ├── main.py                 # 程式進入點
│   ├── formatter.py            # 訊息格式化（共用）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base.py             # DataSource / Notifier 抽象類別
│   │   ├── config.py           # YAML 設定載入器
│   │   └── pipeline.py         # 主流程編排
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── openmeteo.py        # Open-Meteo 資料源實作
│   │   └── cwb.py              # CWB 氣象署資料源實作
│   └── notifiers/
│       ├── __init__.py
│       └── telegram.py         # Telegram 通知頻道實作
├── requirements.txt
└── README.md
```

## 資料源說明

| 特性 | Open-Meteo | CWB 氣象署 |
|------|-----------|-----------|
| API Key 需求 | ❌ 不需要 | ✅ 需要註冊 |
| 全球覆蓋 | ✅ 全球 | ❌ 臺灣限定 |
| 降雨機率 | ✅ | ✅ |
| 紫外線指數 | ❌ | ✅ |
| 舒適度指數 | ❌ | ✅ |
| 天氣綜合描述 | ❌ | ✅ |
| 資料更新頻率 | 每小時 | 每日 4 次 |

## 開發者說明

### 加入新的資料源

1. 在 `src/sources/` 下建立新模組
2. 實作 `DataSource` 抽象類別（`fetch()` + `parse()`）
3. 在 `src/main.py` 中註冊：`register_source("name", NewSource)`
4. 在 `config.yaml` 中新增 source 條目

### 加入新的通知頻道

1. 在 `src/notifiers/` 下建立新模組
2. 實作 `Notifier` 抽象類別（`send()`）
3. 在 `src/main.py` 中註冊：`register_notifier("name", NewNotifier)`
4. 在 `config.yaml` 中新增 notifier 條目

## 授權

MIT License
