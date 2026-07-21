# 開發方案決策文件：天氣預報 Telegram 通知系統

## 📌 決策摘要

| 項目 | 內容 |
|------|------|
| **最終方案** | 🟡🔵 抽象層架構 + 圖表強化混搭（B+C） |
| **決策日期** | 2026-07-21 |
| **參與討論** | Tony Liao（開發者） |
| **共識程度** | ✅ 團隊一致通過 |

---

## 1. 需求回顧

**User Story**：US-20260721-001 — 自動天氣預報 Telegram 通知系統

**核心需求**：
- 每日 07:00 定時推播天氣預報至 Telegram 頻道
- 支援雙資料源：Open-Meteo（主力）+ CWB 氣象署（備援）
- 城市可設定、詳細程度可調（精簡 / 標準 / 完整）
- 錯誤時發送通知而非空白報告
- 支援手動觸發（GitHub Actions workflow_dispatch）

**設計原則**：
- 「資料源擷取（Fetch）」與「推播邏輯（Notify）」嚴格切分
- 設定檔結構化為陣列格式，預留多使用者擴充
- 短期鎖定個人單一頻道，但設計不阻礙縱向擴充

---

## 2. 候選方案

### 🟢 方案 A：現狀模組化強化
- 維持現有 Python 架構，環境變數改為 YAML 設定檔
- 加入 Open-Meteo → CWB 自動 Failover
- **優點**：開發速度快、改動最小
- **缺點**：未來加頻道仍需要改動程式碼

### 🟡 方案 B：抽象層架構
- 導入 `DataSource` / `Notifier` 抽象類別（abc）
- Config-driven：YAML 設定檔驅動整個流程
- **優點**：縱向擴充彈性最大，核心不動
- **缺點**：需要前期重構

### 🔵 方案 C：圖表強化
- 在方案 B 基礎上加入 Matplotlib 靜態圖表附檔
- **優點**：視覺化一目瞭然
- **缺點**：圖表為附加價值，不應做為核心

### 🏆 方案 B + C 混搭（最終選擇）
- Phase 1 先上 B 的核心抽象層
- Phase 2 有餘力再加入 C 的圖表附檔

---

## 3. 權衡評估

| 維度 | 🟢 方案 A | 🟡 方案 B | 🔵 方案 C | 🏆 **B+C** |
|------|:---:|:---:|:---:|:---:|
| 🎯 需求符合度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| ⚡ 開發速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 🔧 維護成本 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 📈 縱向擴充性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 👥 團隊熟悉度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 💰 基礎設施成本 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 🔒 穩定性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 關鍵取捨

| 取捨 | 權衡 | 決策 |
|------|------|------|
| 開發速度 vs 擴充性 | 抽象層需前期投資 | ✅ 值得投入，換取長期彈性 |
| Matplotlib 圖表成本 | 中文字型 + CI 套件 | ✅ Phase 2 選擇性加入 |
| YAML vs 環境變數 | 結構化 vs 簡單 | ✅ YAML，預留多使用者結構 |

---

## 4. 決策理由

### 為什麼選擇此方案
1. **抽象層確保核心不動** — `DataSource` / `Notifier` 介面定義清楚，未來加 Yahoo 天氣、加 LINE Notify 都不改核心編排邏輯
2. **YAML 設定驅動** — 設定檔結構化為陣列，未來多使用者 = YAML 多塞一段，程式碼完全不需要重構
3. **縱向擴充彈性最大化** — 完全符合你「嚴格鎖定單一頻道，但設計思維保留擴充彈性」的原則

### 為什麼放棄其他方案
- **方案 A 現狀強化**：缺少抽象層，加使用者的改動散落在各模組，維護成本隨擴充線性成長
- **純方案 C**：圖表是加分項不是核心價值，不該反過來架構去配合圖表

---

## 5. 行動計畫

### 技術棧

| 層級 | 技術 | 版本 | 備註 |
|------|------|------|------|
| 語言 | Python | 3.11+ | 維持現狀 |
| HTTP | requests | 2.28+ | 維持現狀 |
| 設定檔 | PyYAML | 6.0+ | 新增依賴 |
| 抽象層 | abc | 內建 | Python 標準庫 |
| 圖表 (Phase 2) | Matplotlib | 3.7+ | 選擇性安裝 |
| 排程 | GitHub Actions | - | 維持現狀 |
| Telegram | Bot API (HTTP) | - | 維持現狀 |

### 架構概覽

```
config.yaml
     │
     ▼
┌─────────────────────┐
│    pipeline.py      │ ← 編排核心，不碰資料源與推播細節
│  (逐 user 執行)     │
└──┬──────────────┬───┘
   │              │
   ▼              ▼
┌─────────┐  ┌──────────┐
│ Source  │  │ Notifier │
│ (abc)   │  │ (abc)    │
├─────────┤  ├──────────┤
│ Open-   │  │ Telegram │
│ Meteo   │  │          │
├─────────┤  └──────────┘
│ CWB     │
│(備援)   │
└─────────┘
     │
     ▼
┌──────────┐
│formatter │ ← 共用，不分資料源
│ + chart  │ ← Phase 2
└──────────┘
```

### YAML 設定檔結構（預期）

```yaml
# config.yaml
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

### 建議的專案結構（目標）

```
src/
├── core/
│   ├── __init__.py
│   ├── base.py              ← DataSource / Notifier 抽象類別
│   ├── config.py            ← YAML 載入器，解析設定檔
│   └── pipeline.py          ← 主流程編排
├── sources/
│   ├── __init__.py
│   ├── openmeteo.py         ← Open-Meteo 實作
│   └── cwb.py               ← CWB 氣象署實作
├── notifiers/
│   ├── __init__.py
│   └── telegram.py          ← Telegram 實作
├── charts/
│   ├── __init__.py
│   └── weather_chart.py     ← Phase 2: Matplotlib 圖表
├── formatter.py             ← 訊息格式化（共用）
└── main.py                  ← 進入點
```

### Phase 1 任務拆分

| 優先級 | 任務 | 預估工時 | 說明 |
|--------|------|---------|------|
| P0 | 建立 `core/base.py` 抽象類別 | 1 hr | `DataSource` + `Notifier` abstract base |
| P0 | 建立 `core/config.py` 設定載入器 | 1 hr | PyYAML 讀取 + 環境變數代換 |
| P0 | 建立 `core/pipeline.py` 編排流程 | 1 hr | 逐 user → 逐 source (failover) → format → notify |
| P0 | 將既有 `weather.py` 拆分為 `sources/openmeteo.py` + `sources/cwb.py` | 1 hr | 實作 DataSource 介面 |
| P0 | 將既有 `notifier.py` 改為 `notifiers/telegram.py` | 0.5 hr | 實作 Notifier 介面 |
| P0 | `config.yaml` 根目錄設定檔 | 0.5 hr | 初始單一使用者設定 |
| P1 | GitHub Actions 更新：YAML 設定檔取代環境變數 | 0.5 hr | Secrets 保留，config.yaml 版控 |
| P1 | 更新 `README.md` 文件 | 0.5 hr | 反映新架構與設定方式 |

**預估總工時**：約 **6 小時**（可分 1-2 天完成）

### Phase 2 任務拆分

| 優先級 | 任務 | 預估工時 |
|--------|------|---------|
| P2 | 建立 `charts/weather_chart.py`（7 日氣溫折線圖 + 降雨長條圖） | 2 hr |
| P2 | CI 中文字型安裝（`Noto Sans CJK`） | 0.5 hr |
| P2 | 圖表附檔 Telegram 發送整合 | 0.5 hr |
| P2 | GitHub Actions 可開關圖表功能 | 0.5 hr |

---

## 6. 風險登錄

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|---------|
| 抽象層過度設計 | 低 | 低 | 只有 2 個 DataSource + 1 個 Notifier，介面極簡，不會 over-abstract |
| PyYAML 依賴衝突 | 低 | 低 | 純 Python 套件，無 native extension |
| Matplotlib CI 安裝時間過長 | 中 | 低 | Phase 2 選擇性安裝，可透過 GitHub Actions cache 加速 |
| CWB API Key 過期未更新 | 中 | 低 | Open-Meteo 為主力，CWB 僅備援，不影響主要功能 |

---

## 📝 決策後續

- ✅ 本文件已存至 `docs/tech-decision-天氣預報通知系統-2026-07-21.md`
- ✅ 已納入版本控制
- 📌 Phase 1 完成後建議重新檢視本決策，確認方向正確
- 📌 Phase 2 啟動前請確認 Matplotlib 是否真的必要

---

*產生日期：2026-07-21 | 使用 Tech Assessment Generator 引導討論*
