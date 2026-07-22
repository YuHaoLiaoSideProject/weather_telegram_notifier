#!/usr/bin/env node
/**
 * Generate a weather forecast card image using an HTML template + Puppeteer.
 *
 * Usage:
 *   node src/charts/generate_card.js < input.json
 *   node src/charts/generate_card.js --forecast '[...]' --location '臺北市' --output /tmp/card.png
 *
 * Input JSON (stdin or --forecast):
 *   {
 *     "location": "臺北市",
 *     "source": "Open-Meteo",
 *     "forecast": [
 *       {
 *         "date": "2026-07-22",
 *         "weekday": "週三",
 *         "wx": "☀️ 晴天",
 *         "max_t": 34,
 *         "min_t": 26,
 *         "pop": 10
 *       },
 *       ...
 *     ]
 *   }
 */

const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

// ── Parse arguments ──────────────────────────────────────────────────────────

const args = {};
process.argv.slice(2).forEach((arg, i, arr) => {
  if (arg.startsWith("--")) {
    const key = arg.slice(2);
    const val = arr[i + 1];
    if (val && !val.startsWith("--")) {
      args[key] = val;
    } else {
      args[key] = true;
    }
  }
});

// ── Helpers ──────────────────────────────────────────────────────────────────

const WEEKDAY_MAP = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];

function shortWx(wx) {
  if (!wx) return "--";
  for (const [kw, label] of [
    ["雷暴", "雷雨"],
    ["冰雹", "冰雹"],
    ["大雪", "大雪"],
    ["小雪", "小雪"],
    ["大雨", "大雨"],
    ["毛毛雨", "細雨"],
    ["陣雨", "陣雨"],
    ["凍雨", "凍雨"],
    ["雨", "雨天"],
    ["霧淞", "霧淞"],
    ["霧", "有霧"],
    ["晴天", "晴天"],
    ["晴朗", "晴天"],
    ["多雲時晴", "晴時雲"],
    ["多雲", "多雲"],
    ["雪粒", "雪"],
    ["雪", "下雪"],
  ]) {
    if (wx.includes(kw)) return label;
  }
  return "☁";
}

// ── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  // Read input
  let input;
  if (args.forecast) {
    input = JSON.parse(args.forecast);
  } else {
    const raw = fs.readFileSync(0, "utf-8");
    input = JSON.parse(raw);
  }

  const { location = "未知", source = "開放氣象 API", forecast = [] } = input;
  const outputPath = args.output || "/tmp/weather_card.png";

  // Build day cards HTML
  const daysHtml = forecast
    .map((day) => {
      const dt = new Date(day.date + "T12:00:00");
      const weekdayEn = WEEKDAY_MAP[dt.getDay()];
      const monthDay = `${String(dt.getMonth() + 1).padStart(2, "0")}/${String(
        dt.getDate()
      ).padStart(2, "0")}`;
      const maxT = day.max_t != null ? `${Math.round(day.max_t)}°C` : "--°C";
      const minT = day.min_t != null ? `${Math.round(day.min_t)}°C` : "--°C";
      const pop = day.pop != null ? Math.round(day.pop) : null;
      const rainHtml =
        pop != null
          ? `<div class="rain-info">💧 ${pop}%</div>`
          : `<div class="rain-info" style="color:#aaa">--</div>`;

      return `
            <td class="day-card">
                <div class="day-name">${weekdayEn}</div>
                <div class="date">${monthDay}</div>
                <div class="weather-icon">${shortWx(day.wx)}</div>
                <div class="temp-range">${minT} - ${maxT}</div>
                ${rainHtml}
            </td>`;
    })
    .join("\n");

  // Read template
  const templatePath =
    args.template ||
    path.join(__dirname, "weather_card.html");
  let html = fs.readFileSync(templatePath, "utf-8");

  // Replace placeholders
  const now = new Date();
  const taipeiOffset = 8 * 60;
  const tw = new Date(now.getTime() + taipeiOffset * 60 * 1000);
  const generated = tw.toISOString().slice(0, 16).replace("T", " ") + " CST";

  html = html
    .replace("__LOCATION__", location)
    .replace("__DAYS__", daysHtml)
    .replace("__SOURCE__", source)
    .replace("__GENERATED__", generated);

  // Launch browser & screenshot
  const browser = await puppeteer.launch({
    executablePath: "/usr/bin/chromium",
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle0" });

  // Get card dimensions
  const card = await page.$("#card");
  const box = await card.boundingBox();

  await page.screenshot({
    path: outputPath,
    clip: {
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height,
    },
  });

  await browser.close();
  console.log(outputPath);
})();
