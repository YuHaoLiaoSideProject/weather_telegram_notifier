@weather @telegram @notification @p0
Feature: 自動天氣預報 Telegram 通知系統
  As a 公開 Telegram 頻道的訂閱者
  I want 每天早上定時收到天氣預報通知，內容包含氣溫、降雨機率、風速等完整天氣資訊
  So that 我可以出門前掌握當日天氣狀況，做好行程規劃與衣物準備

  # ==========================================================================
  # Happy Path - 正常操作流程
  # ==========================================================================

  @weather-happy-path @smoke
  Scenario: 每日定時排程成功抓取天氣並發送通知
    Given 系統已正常運作
    And 時間為每日 07:00（台灣時間）
    When GitHub Actions 排程 cron "0 23 * * *" 觸發執行
    And 系統向 Open-Meteo API 請求天氣資料
    And 系統格式化天氣訊息為完整模式
    And 系統透過 Telegram Bot API 發送訊息至指定頻道
    Then Telegram API 回傳成功狀態 "ok": true
    And 訂閱者在頻道中收到天氣預報通知
    And 通知內容包含日期、星期、天氣現象、溫度與降雨機率

  @weather-happy-path @manual
  Scenario: 手動觸發成功發送通知
    Given 使用者在 GitHub Actions 頁面
    When 使用者點擊「Run workflow」按鈕
    And 選擇城市 "高雄市"
    And 點擊「Run」確認執行
    Then Workflow 立即啟動
    And 系統在 30 秒內完成抓取與發送
    And 訂閱者收到高雄市的天氣預報通知

  @weather-happy-path @openmeteo
  Scenario: 使用 Open-Meteo 資料源擷取 7 日預報
    Given 系統已設定資料來源為 "openmeteo"
    When 系統向 Open-Meteo API 發送請求
    Then 系統成功取得 7 日天氣預報資料
    And 每筆資料包含天氣代碼、最高/低溫、體感溫度、降雨機率、風速風向

  @weather-happy-path @cwb
  Scenario: 使用 CWB 氣象署資料源擷取預報
    Given 系統已設定資料來源為 "cwb"
    And CWB_API_KEY 為有效的授權碼
    When 系統向 CWB API 發送請求
    Then 系統成功取得天氣預報資料
    And 資料包含 PoP12h、溫度、濕度、風速、紫外線指數等 15 項天氣元素

  @weather-happy-path @city
  Scenario: 查詢不同城市的天氣預報
    Given 系統已設定 WEATHER_LOCATION 為 "臺北市"
    When 使用者變更 WEATHER_LOCATION 為 "高雄市"
    And 系統重新執行天氣查詢
    Then 系統回傳高雄市的天氣預報
    And 通知中的地點標示為 "高雄市"

  # ==========================================================================
  # Alternative Flow - 替代流程與分支
  # ==========================================================================

  @weather-alternative @detail
  Scenario: 精簡模式只顯示核心天氣資訊
    Given 系統已設定 DETAIL_LEVEL 為 "basic"
    When 系統格式化天氣訊息
    Then 每筆每日預報僅包含：
      | 欄位        |
      | 天氣現象    |
      | 最高/低溫   |
      | 降雨機率    |
    And 不包含體感溫度、濕度、風速、紫外線指數

  @weather-alternative @detail
  Scenario: 標準模式顯示適中資訊量
    Given 系統已設定 DETAIL_LEVEL 為 "standard"
    When 系統格式化天氣訊息
    Then 每筆每日預報包含天氣現象、溫度、體感溫度、降雨機率、風速風向
    And 不包含紫外線指數與天氣描述

  @weather-alternative @detail
  Scenario: 完整模式顯示所有可用資訊
    Given 系統已設定 DETAIL_LEVEL 為 "full"
    When 系統格式化天氣訊息
    Then 每筆每日預報包含所有可用天氣欄位
    And 若資料源有提供，包含紫外線指數與天氣描述

  # ==========================================================================
  # Error Handling - 錯誤處理與異常狀況
  # ==========================================================================

  @weather-error @telegram
  Scenario: Telegram Bot Token 無效時發送失敗通知
    Given TELEGRAM_BOT_TOKEN 為無效的 Token "invalid_token_123"
    When 系統嘗試透過 Telegram API 發送訊息
    Then Telegram API 回傳 401 Unauthorized
    And 系統記錄 "TELEGRAM_BOT_TOKEN is not set" 錯誤日誌
    And 系統發送「天氣預報擷取失敗」通知（若 Chat ID 正確）

  @weather-error @telegram
  Scenario: 指定的 Chat ID 不存在
    Given TELEGRAM_CHAT_ID 指向未將 Bot 加入的頻道
    When 系統嘗試發送訊息
    Then Telegram API 回傳 403 Forbidden
    And 系統記錄明確的權限錯誤日誌
    And 排程執行標記為失敗

  @weather-error @api
  Scenario: Open-Meteo API 無法連線
    Given 網路連線中斷或 Open-Meteo API 服務異常
    When 系統向 Open-Meteo API 發送請求
    Then 系統捕獲 requests.RequestException
    And 系統不產生空白的天氣報告
    And 系統發送「無法取得天氣資料」錯誤通知至 Telegram

  @weather-error @api
  Scenario: CWB API Key 無效或過期
    Given 系統設定資料來源為 "cwb"
    And CWB_API_KEY 為過期或無效的金鑰
    When 系統向 CWB API 發送請求
    Then API 回傳 403 或 401 狀態碼
    And 系統拋出授權失敗錯誤
    And 系統發送「API 授權失敗」通知至 Telegram

  @weather-error @input
  Scenario: 輸入不存在的城市名稱
    Given 系統執行查詢
    When 使用者輸入不存在的城市名稱 "Atlantis"
    Then 系統拋出 ValueError「Unknown location: 'Atlantis'」
    And 系統發送錯誤通知，包含可用的城市清單
    And 系統不發送任何天氣預報

  @weather-error @data
  Scenario: API 回傳空資料或格式異常
    Given API 回傳空 JSON 或缺少必要欄位
    When 系統解析 API 回傳資料
    Then 系統拋出解析錯誤 "No temperature data found"
    Or 拋出 "No daily data in Open-Meteo response"
    And 系統發送錯誤通知，不產生不完整的氣象報告

  # ==========================================================================
  # Edge Cases - 邊界情況與極端值
  # ==========================================================================

  @weather-edge @performance
  Scenario: API 回應時間超過 30 秒
    Given API 回應時間為 35 秒
    When 系統發送 API 請求（timeout=30）
    Then 系統捕獲 requests.Timeout 或 requests.ConnectionError
    And 系統記錄逾時錯誤
    And 系統發送錯誤通知

  @weather-edge @data
  Scenario: 降雨機率為 0% 時精簡模式不顯示
    Given 某日的降雨機率為 0%
    And DETAIL_LEVEL 為 "basic"
    When 系統格式化該日預報
    Then 該日不顯示降雨機率欄位

  @weather-edge @data
  Scenario: 極端溫度值顯示正確
    Given 氣象資料回傳最高溫度 39°C 或最低溫度 2°C
    When 系統格式化溫度欄位
    Then 溫度顯示 "最高 39°C" 或 "最低 2°C"
    And 對應的 Emoji 正確顯示（高溫 🥵，低溫 🥶）

  @weather-edge @schedule
  Scenario: GitHub Actions 排程延遲執行
    Given GitHub Actions 佇列等待 25 分鐘
    When 排程觸發執行
    Then 系統仍正常抓取並發送天氣預報
    And 通知中的時間戳記顯示實際執行時間

  # ==========================================================================
  # Business Rules - 商業規則驗證
  # ==========================================================================

  @weather-rule @security
  Scenario: API Token 與金鑰不寫入原始碼
    Given TELEGRAM_BOT_TOKEN 與 CWB_API_KEY 存放於 GitHub Secrets
    When 檢查原始碼檔案
    Then 原始碼中不包含任何 Token 或金鑰字串
    And 所有機敏資訊僅透過 os.environ 讀取

  @weather-rule @config
  Scenario: 所有設定透過環境變數管理
    Given 系統啟動
    When 系統讀取環境變數
    Then 以下參數可透過環境變數設定：
      | 變數名稱         | 預設值     |
      | TELEGRAM_BOT_TOKEN | 無        |
      | TELEGRAM_CHAT_ID   | 無        |
      | WEATHER_LOCATION   | 臺北市     |
      | WEATHER_SOURCE     | openmeteo  |
      | DETAIL_LEVEL       | full       |
      | CWB_API_KEY        | 無        |
    And 環境變數未設定時使用預設值

  @weather-rule @reliability
  Scenario: Open-Meteo 失效時可切換至 CWB
    Given 系統預設使用 Open-Meteo
    When Open-Meteo API 連續失敗
    And 使用者將 WEATHER_SOURCE 切換為 "cwb"
    Then 系統使用 CWB API 取得天氣資料
    And 通知標示資料來源為「中央氣象署 CWB」
