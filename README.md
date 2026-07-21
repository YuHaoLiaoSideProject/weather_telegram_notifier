# 🌤 Weather Telegram Notifier

自動抓取天氣預報，並透過 Telegram Bot 定時推送到你的手機。

## 功能

- ✅ 每日自動推送天氣預報（預設早上 7:00）
- ✅ 支援兩大資料源：
  - **Open-Meteo**（免費、免 API Key、全球覆蓋）← 預設
  - **中央氣象署 CWB 開放資料 API**（臺灣地區資料更詳細）
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

### 3. 設定 GitHub Secrets

在 GitHub Repo → **Settings → Secrets and variables → Actions** 新增：

| Secret | 說明 | 必要 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（從 @BotFather 取得） | ✅ |
| `TELEGRAM_CHAT_ID` | 接收通知的 Chat ID | ✅ |
| `CWB_API_KEY` | CWB API Key（僅 source=cwb 時需要） | ❌ |

### 4. 啟用 GitHub Actions

Push 到 GitHub 後，Workflow 會自動啟用。
- 預設排程：**每日 UTC 23:00（台灣時間 07:00）**
- 也可在 GitHub → Actions → **Weather Forecast Notifier** → **Run workflow** 手動執行

## 自訂設定

### 變更城市

在 `.github/workflows/weather_forecast.yml` 中修改 `WEATHER_LOCATION`：

```yaml
WEATHER_LOCATION: '高雄市'
```

或手動執行時在 GitHub UI 輸入城市名稱。

### 變更資料源

#### Open-Meteo（預設，免 API Key）

支援全球城市，無需任何金鑰。

#### CWB 氣象署 API（臺灣地區）

1. 前往 [氣象署開放資料平臺](https://opendata.cwb.gov.tw/) 註冊
2. 取得 API Key（授權碼）
3. 在 GitHub Secrets 新增 `CWB_API_KEY`
4. 在 Workflow 中設定 `WEATHER_SOURCE: cwb`

## 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# 執行（僅顯示，不發送）
python -m src.main --location 臺北市 --dry-run

# 執行並發送
python -m src.main --location 高雄市

# 使用 CWB API
python -m src.main --source cwb --location 臺北市
```

## 專案結構

```
weather_telegram_notifier/
├── .github/workflows/
│   └── weather_forecast.yml    # GitHub Actions 排程
├── src/
│   ├── __init__.py
│   ├── main.py                 # 程式進入點
│   ├── weather.py              # 天氣資料擷取（CWB / Open-Meteo）
│   ├── formatter.py            # 訊息格式化
│   └── notifier.py             # Telegram 發送
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

## 授權

MIT License
