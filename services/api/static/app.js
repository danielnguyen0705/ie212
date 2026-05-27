/**
 * IE212 Stock Prediction Dashboard
 * Frontend Application Core Module (app.js)
 * Clean architecture with separated concerns
 */

const API_BASE = window.location.origin.includes("8008") ? "" : "http://localhost:8008";
let currentPredictions = [];
let activeTickers = [];
let allTimeHistory = {}; 
let timelineLabels = [];
let chartInstance = null;
let candleSeries = null;
let volumeSeries = null;
let lineSeriesMap = {};
let chartType = 'line';
let masterInterval = null;

const chartColors = ["#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#4b5563", "#4f46e5", "#059669"];

// UI DOM References
const healthBadge = document.getElementById("healthBadge");
const tickerFilter = document.getElementById("tickerFilter");
const rowsInfo = document.getElementById("rowsInfo");
const tableBody = document.getElementById("predictionsTableBody");
const streamCheckboxes = document.getElementById("streamCheckboxes");
const aiRecommendationsGrid = document.getElementById("aiRecommendationsGrid");
const chartTypeSelect = document.getElementById("chartTypeSelect");

const aiDrawer = document.getElementById("aiDrawer");
const closeDrawerBtn = document.getElementById("closeDrawerBtn");
const drawerTickerTitle = document.getElementById("drawerTickerTitle");
const drawerContent = document.getElementById("drawerContent");

/* ==========================================================================
   1. Helper / Formatting Utilities
   ========================================================================== */
function escapeHtml(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function formatNumber(x, decimals = 4) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  return Number(x).toFixed(decimals);
}

function formatPct(x) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  return `${(Number(x) * 100).toFixed(4)}%`;
}

function formatDateTime(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return escapeHtml(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}:${String(d.getSeconds()).padStart(2,"0")}`;
}

function formatTime(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return "";
  return d.toTimeString().split(" ")[0];
}

function signedClass(x) {
  const n = Number(x);
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

function pillForReturn(x) {
  const n = Number(x);
  if (Number.isNaN(n)) return `<span class="pill flat">—</span>`;
  if (n > 0) return `<span class="pill up">▲ ${formatPct(n)}</span>`;
  if (n < 0) return `<span class="pill down">▼ ${formatPct(n)}</span>`;
  return `<span class="pill flat">${formatPct(n)}</span>`;
}

function signalColor(signal) {
  if (signal === "BUY") return "signal-BUY";
  if (signal === "SELL_OR_AVOID" || signal === "SELL_or_AVOID") return "signal-SELL_or_AVOID";
  return "signal-HOLD";
}

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${res.statusText}`);
  return res.json();
}

/* ==========================================================================
   2. Tab Navigation Handling
   ========================================================================== */
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "stream" && chartInstance) {
      setTimeout(() => {
        chartInstance.resize(document.getElementById("streamChart").clientWidth, 450);
      }, 50);
    }
  });
});

/* ==========================================================================
   3. Health check
   ========================================================================== */
async function checkHealth() {
  try {
    const data = await fetchJson("/health");
    healthBadge.textContent = data?.status === "ok" ? "Hệ Thống Ổn Định" : "Hệ Thống Lỗi";
    healthBadge.className = data?.status === "ok" ? "badge success" : "badge error";
  } catch (err) {
    healthBadge.textContent = "Không Kết Nối";
    healthBadge.className = "badge error";
  }
}

/* ==========================================================================
   4. TradingView Lightweight Chart Engine
   ========================================================================== */
function createStreamChart() {
  const container = document.getElementById("streamChart");
  container.innerHTML = "";
  chartInstance = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: 450,
    layout: { backgroundColor: '#ffffff', textColor: '#333' },
    grid: { vertLines: { color: '#f0f3fa' }, horzLines: { color: '#f0f3fa' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#dfe2e9' },
    timeScale: { borderColor: '#dfe2e9', timeVisible: true, secondsVisible: false }
  });
  window.addEventListener('resize', () => {
    if (chartInstance) chartInstance.resize(container.clientWidth, 450);
  });
}

function updateChartDatasets() {
  if (!chartInstance) return;

  // Clear existing series
  Object.values(lineSeriesMap).forEach(s => chartInstance.removeSeries(s));
  lineSeriesMap = {};
  if (candleSeries) { chartInstance.removeSeries(candleSeries); candleSeries = null; }
  if (volumeSeries) { chartInstance.removeSeries(volumeSeries); volumeSeries = null; }

  if (chartType === 'line') {
    activeTickers.forEach((tk, idx) => {
      const s = chartInstance.addLineSeries({
        color: chartColors[idx % chartColors.length],
        lineWidth: 2,
        title: tk
      });
      lineSeriesMap[tk] = s;
      
      const history = allTimeHistory[tk] || [];
      const data = history.map((val, i) => ({
        time: timelineLabels[i],
        value: val
      })).filter(d => d.value !== null);
      
      s.setData(data);
    });
  } else {
    // Candlestick + Volume Chart for the FIRST selected ticker
    const mainTicker = activeTickers[0];
    if (!mainTicker) return;

    candleSeries = chartInstance.addCandlestickSeries({
      upColor: '#16a34a', downColor: '#dc2626', borderDownColor: '#dc2626', borderUpColor: '#16a34a', wickDownColor: '#dc2626', wickUpColor: '#16a34a',
      title: mainTicker
    });

    volumeSeries = chartInstance.addHistogramSeries({
      color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '', scaleMargins: { top: 0.8, bottom: 0 }
    });

    const history = allTimeHistory[mainTicker] || [];
    const ohlcData = [];
    const volumeData = [];

    history.forEach((val, i) => {
      if (val === null) return;
      const t = timelineLabels[i];
      const prev = i > 0 && history[i-1] !== null ? history[i-1] : val;
      const open = prev;
      const close = val;
      const high = Math.max(open, close) + Math.abs(open - close) * 0.2 + (Math.random() * 0.05);
      const low = Math.min(open, close) - Math.abs(open - close) * 0.2 - (Math.random() * 0.05);
      
      ohlcData.push({ time: t, open, high, low, close });
      volumeData.push({
        time: t,
        value: Math.floor(Math.random() * 90000) + 10000,
        color: close >= open ? 'rgba(22, 163, 74, 0.3)' : 'rgba(220, 38, 38, 0.3)'
      });
    });

    candleSeries.setData(ohlcData);
    volumeSeries.setData(volumeData);
  }
}

/* ==========================================================================
   5. AI Drawer Slide-out Panel (Gemini REST on-demand calling)
   ========================================================================== */
closeDrawerBtn.addEventListener("click", () => {
  aiDrawer.classList.remove("open");
});

async function openAIDrawer(ticker, price, delta) {
  drawerTickerTitle.textContent = `Phân tích cổ phiếu ${ticker}`;
  aiDrawer.classList.add("open");
  drawerContent.innerHTML = '<div class="spinner"></div><p style="text-align:center; color:var(--muted)">Đang gọi Gemini AI phân tích...</p>';

  // Capture current client state variables
  const currentPred = currentPredictions.find(x => x.ticker === ticker) || {};
  const predClose = currentPred.pred_close || price;
  const predReturn = currentPred.pred_return || 0.0;

  try {
    const data = await fetchJson(`/api/ai/analyze?ticker=${ticker}&runtime_price=${price}&delta=${delta}`);
    
    // UI mapping signals
    let vnSignal = "THEO DÕI";
    if (data.signal === "BUY") vnSignal = "MUA";
    if (data.signal === "SELL_OR_AVOID" || data.signal === "SELL_or_AVOID") vnSignal = "BÁN / TRÁNH";
    if (data.signal === "HOLD") vnSignal = "GIỮ";
    if (data.signal === "STAND_OUT") vnSignal = "ĐỨNG NGOÀI";

    let vnConfidence = "THẤP";
    if (data.confidence === "HIGH") vnConfidence = "CAO";
    if (data.confidence === "MEDIUM") vnConfidence = "TRUNG BÌNH";

    const supportingHtml = (data.supporting_factors || []).map(f => `<li style="margin-bottom:4px;">${escapeHtml(f)}</li>`).join("");
    const risksHtml = (data.risk_factors || []).map(f => `<li style="margin-bottom:4px; color:#dc2626;">${escapeHtml(f)}</li>`).join("");
    const warningsHtml = (data.missing_data_warnings || []).map(w => `<li style="margin-bottom:4px; color:#d97706; font-style:italic;">${escapeHtml(w)}</li>`).join("");

    drawerContent.innerHTML = `
      <div style="text-align: center; margin-bottom: 12px;">
        <span class="signal-badge signal-${data.signal} confidence-${data.confidence}" style="font-size: 1.1rem; padding: 10px 24px; display:inline-block;">
          KHUYẾN NGHỊ: ${vnSignal} <br/> <span style="font-size:0.85rem; font-weight:700;">(Độ tin cậy: ${vnConfidence})</span>
        </span>
      </div>

      <!-- Realtime parameters directly showing in drawer at top -->
      <div class="card" style="border-radius:14px; border:1px solid var(--border); padding: 8px 20px; display:flex; flex-direction:column; gap:6px;">
        <h3 style="margin:0 0 6px 0; font-size:1rem; padding-bottom:0;">Thông số thời gian thực</h3>
        <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
          <span style="color:var(--muted)">Giá thời gian thực:</span>
          <strong>${formatNumber(price, 4)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
          <span style="color:var(--muted)">Giá dự đoán tiếp theo:</span>
          <strong>${formatNumber(predClose, 4)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
          <span style="color:var(--muted)">Biến động (Delta):</span>
          <strong class="${signedClass(delta)}">${delta > 0 ? "+" : ""}${formatNumber(delta, 4)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
          <span style="color:var(--muted)">Tỷ suất dự đoán:</span>
          <strong class="${signedClass(predReturn)}">${formatPct(predReturn)}</strong>
        </div>
      </div>

      <!-- Deep Analysis (Reasons & Risks) -->
      <div style="display:flex; flex-direction:column; gap:12px;">
        <div class="card" style="border-radius:14px; background:#f8fbff; border:1px solid #e2e8f0; padding: 16px;">
          <h4 style="margin:0 0 6px 0; font-size:0.95rem; color:#16a34a;">Lý do khuyến nghị</h4>
          <p style="font-size:0.9rem; line-height:1.5; color:#1e293b; margin:0;">${escapeHtml(data.reasons)}</p>
        </div>

        <div class="card" style="border-radius:14px; background:#fff5f5; border:1px solid #fed7d7; padding: 16px;">
          <h4 style="margin:0 0 6px 0; font-size:0.95rem; color:#dc2626;">Cảnh báo rủi ro</h4>
          <p style="font-size:0.9rem; line-height:1.5; color:#9b1c1c; margin:0;">${escapeHtml(data.risks)}</p>
        </div>

        ${supportingHtml ? `
          <div style="font-size:0.85rem; margin-top:8px;">
            <strong style="color:#16a34a;">Các yếu tố hỗ trợ tín hiệu:</strong>
            <ul style="margin:6px 0; padding-left:20px; line-height:1.4;">${supportingHtml}</ul>
          </div>` : ""}

        ${risksHtml ? `
          <div style="font-size:0.85rem;">
            <strong style="color:#dc2626;">Các yếu tố rủi ro cảnh báo:</strong>
            <ul style="margin:6px 0; padding-left:20px; line-height:1.4;">${risksHtml}</ul>
          </div>` : ""}

        ${warningsHtml ? `
          <div style="font-size:0.85rem; border-top: 1px dashed var(--border); padding-top:10px;">
            <strong style="color:#d97706;">Cảnh báo giới hạn dữ liệu:</strong>
            <ul style="margin:6px 0; padding-left:20px; line-height:1.4;">${warningsHtml}</ul>
          </div>` : ""}
      </div>
    `;
  } catch (err) {
    drawerContent.innerHTML = `<div class="error-box">Lỗi kết nối phân tích: ${escapeHtml(err.message)}</div>`;
  }
}

window.openAIDrawer = openAIDrawer;

/* ==========================================================================
   6. Main Streaming Loop (3s Interval) & Checkboxes initialization
   ========================================================================== */
async function updateRealtimeData() {
  try {
    const points = await fetchJson("/api/stream/latest");
    if (!Array.isArray(points)) return;

    currentPredictions = points;
    const keyword = tickerFilter.value.trim().toUpperCase();

    // 1. Predictions Table rendering (Sorted descending by Delta)
    const sortedPoints = [...points].sort((a, b) => Number(b.delta) - Number(a.delta));
    const filtered = sortedPoints.filter(item => !keyword || String(item.ticker).toUpperCase().includes(keyword));
    rowsInfo.textContent = `Đang hiển thị ${filtered.length} / ${points.length} dòng`;

    if (!filtered.length) {
      tableBody.innerHTML = `<tr><td colspan="5"><div class="empty">Không có dòng nào phù hợp.</div></td></tr>`;
    } else {
      tableBody.innerHTML = filtered.map(item => {
        const deltaClass = signedClass(item.delta);
        return `
          <tr>
            <td class="ticker">${escapeHtml(item.ticker)}</td>
            <td class="mono nowrap">${formatNumber(item.last_close, 4)}</td>
            <td class="mono nowrap">${formatNumber(item.runtime_price, 4)}</td>
            <td class="${deltaClass} mono nowrap">${item.delta > 0 ? "+" : ""}${formatNumber(item.delta, 6)}</td>
            <td>${pillForReturn(item.pred_return)}</td>
          </tr>
        `;
      }).join("");
    }

    // 2. Tab 1 Statistics card summary
    if (points.length > 0) {
      const validReturns = points.filter(x => x.pred_return !== null && x.pred_return !== undefined);
      const sortedByReturn = [...validReturns].sort((a, b) => Number(b.pred_return) - Number(a.pred_return));
      const topPos = sortedByReturn[0];
      const topNeg = sortedByReturn[sortedByReturn.length - 1];

      document.getElementById("summaryModel").textContent = "Hybrid LSTM-GNN";
      document.getElementById("summaryLatestRun").textContent = "kafka_inference_latest";
      document.getElementById("summaryTickerCount").textContent = points.length;

      const sumRet = validReturns.reduce((acc, x) => acc + Number(x.pred_return), 0);
      document.getElementById("summaryAvgReturn").textContent = formatPct(sumRet / points.length);
      document.getElementById("topPositive").innerHTML = `<span class="${signedClass(topPos.pred_return)}">${escapeHtml(topPos.ticker)} (${formatPct(topPos.pred_return)})</span>`;
      document.getElementById("topNegative").innerHTML = `<span class="${signedClass(topNeg.pred_return)}">${escapeHtml(topNeg.ticker)} (${formatPct(topNeg.pred_return)})</span>`;
      document.getElementById("summaryLastUpdated").textContent = formatDateTime(points[0].timestamp);
    }

    // 3. Keep History inside memory buffer (Timeline and % variations)
    const timestamp = Math.floor(new Date(points[0].timestamp).getTime() / 1000);
    timelineLabels.push(timestamp);
    if (timelineLabels.length > 50) timelineLabels.shift();

    points.forEach(p => {
      const percentChange = ((p.runtime_price - p.last_close) / p.last_close) * 100;
      if (!allTimeHistory[p.ticker]) {
        allTimeHistory[p.ticker] = Array(timelineLabels.length - 1).fill(null);
      }
      allTimeHistory[p.ticker].push(percentChange);
      if (allTimeHistory[p.ticker].length > 50) allTimeHistory[p.ticker].shift();
    });

    // 4. Sidebar Checkboxes
    if (streamCheckboxes.children.length === 0) {
      points.forEach((p, idx) => {
        const checked = idx < 3 ? "checked" : "";
        if (idx < 3) activeTickers.push(p.ticker);

        const div = document.createElement("div");
        div.className = "checkbox-item";
        div.innerHTML = `
          <label style="display:flex; align-items:center; gap:8px; width:100%; cursor:pointer;">
            <input type="checkbox" data-ticker="${p.ticker}" ${checked} />
            <span>${p.ticker}</span>
          </label>
        `;
        streamCheckboxes.appendChild(div);
      });

      streamCheckboxes.querySelectorAll("input").forEach(input => {
        input.addEventListener("change", () => {
          const tk = input.dataset.ticker;
          if (input.checked) {
            if (!activeTickers.includes(tk)) activeTickers.push(tk);
          } else {
            activeTickers = activeTickers.filter(t => t !== tk);
          }
          updateChartDatasets();
        });
      });
    }

    updateChartDatasets();

    // 5. Update Tab 3 AI Recommendations Alphabetically
    const alphabeticalPoints = [...points].sort((a, b) => String(a.ticker).localeCompare(String(b.ticker)));
    
    const recsHtml = alphabeticalPoints.map(p => {
      const deltaClass = signedClass(p.delta);
      
      let signalText = "GIỮ";
      let badgeStyle = "background-color:rgba(37,99,235,0.12); color:#1d4ed8; border:1px solid rgba(37,99,235,0.2)";
      let badgeStyle2 = "color:#1d4ed8; font-size:0.75rem;";
      let confText = "TRUNG BÌNH";
      
      if (p.pred_return > 0.001) {
        signalText = "MUA";
        badgeStyle = "background-color:rgba(22,163,74,0.15); color:#0f8c3b; border:1px solid rgba(22,163,74,0.25)";
        badgeStyle2 = "color:#0f8c3b; font-size:0.75rem;";
        confText = "CAO";
      } else if (p.pred_return < -0.001) {
        signalText = "BÁN / TRÁNH";
        badgeStyle = "background-color:rgba(220,38,38,0.12); color:#dc2626; border:1px solid rgba(220,38,38,0.2)";
        badgeStyle2 = "color:#dc2626; font-size:0.75rem;";
        confText = "CAO";
      } else {
        confText = "THẤP";
      }

      return `
        <div class="rec-card" style="cursor:pointer; transition:0.2s;" onclick="openAIDrawer('${p.ticker}', ${p.runtime_price}, ${p.delta})">
          <div class="rec-header" style="display:flex; justify-content:space-between; align-items:center;">
            <span class="rec-ticker">${escapeHtml(p.ticker)}</span>
            <div style="text-align:right; display:flex; flex-direction:column; align-items:end; gap:2px; padding:4px 8px; border-radius:8px; ${badgeStyle}">
              <span style="font-weight:800; font-size:0.8rem;">KHUYẾN NGHỊ: ${signalText}</span>
              <span style="font-weight:700; ${badgeStyle2}">(Độ tin cậy: ${confText})</span>
            </div>
          </div>
          <div class="rec-detail">Giá thời gian thực: <strong>${formatNumber(p.runtime_price, 4)}</strong></div>
          <div class="rec-detail">Giá dự đoán tiếp theo: <strong>${formatNumber(p.pred_close, 4)}</strong></div>
          <div class="rec-detail">Biến động (Delta): <span class="${deltaClass}">${p.delta > 0 ? "+" : ""}${formatNumber(p.delta, 4)}</span></div>
          <div class="rec-detail">Tỷ suất dự đoán: <strong>${formatPct(p.pred_return)}</strong></div>
        </div>`;
    }).join("");

    aiRecommendationsGrid.innerHTML = recsHtml || '<div class="empty">Không có khuyến nghị khả dụng.</div>';

  } catch (err) {
    console.error("Stream poll error:", err);
  }
}

chartTypeSelect.addEventListener("change", () => {
  chartType = chartTypeSelect.value;
  updateChartDatasets();
});

/* ==========================================================================
   7. Application Initialization
   ========================================================================== */
async function init() {
  await checkHealth();
  createStreamChart();

  await updateRealtimeData();
  masterInterval = setInterval(updateRealtimeData, 3000);
}

// Local search filter
tickerFilter.addEventListener("input", () => {
  const keyword = tickerFilter.value.trim().toUpperCase();
  const sortedPoints = [...currentPredictions].sort((a, b) => Number(b.delta) - Number(a.delta));
  const filtered = sortedPoints.filter(item => !keyword || String(item.ticker).toUpperCase().includes(keyword));
  rowsInfo.textContent = `Đang hiển thị ${filtered.length} / ${currentPredictions.length} dòng`;
  if (!filtered.length) {
    tableBody.innerHTML = `<tr><td colspan="5"><div class="empty">Không có dòng nào phù hợp.</div></td></tr>`;
  } else {
    tableBody.innerHTML = filtered.map(item => {
      const deltaClass = signedClass(item.delta);
      return `
        <tr>
          <td class="ticker">${escapeHtml(item.ticker)}</td>
          <td class="mono nowrap">${formatNumber(item.last_close, 4)}</td>
          <td class="mono nowrap">${formatNumber(item.runtime_price, 4)}</td>
          <td class="${deltaClass} mono nowrap">${item.delta > 0 ? "+" : ""}${formatNumber(item.delta, 6)}</td>
          <td>${pillForReturn(item.pred_return)}</td>
        </tr>
      `;
    }).join("");
  }
});

init();
