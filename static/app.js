const state = {
  cityConfigs: {},
  result: null,
  step: "stage1",
  tableTab: "stage1",
  customRdcMode: false,
  customRdcs: [],
  customViolations: [],
  map: null,
  layers: {},
};

const els = {
  modelForm: document.getElementById("modelForm"),
  runSampleBtn: document.getElementById("runSampleBtn"),
  focusCity: document.getElementById("focusCity"),
  pStepper: document.getElementById("pStepper"),
  pValues: document.getElementById("pValues"),
  status: document.getElementById("status"),
  cityWacc: document.getElementById("cityWacc"),
  cityNpvDefault: document.getElementById("cityNpvDefault"),
  cityDppDefault: document.getElementById("cityDppDefault"),
  npvThreshold: document.getElementById("npvThreshold"),
  dppThreshold: document.getElementById("dppThreshold"),
  summaryCards: document.getElementById("summaryCards"),
  costBars: document.getElementById("costBars"),
  scenarioCards: document.getElementById("scenarioCards"),
  hardAlerts: document.getElementById("hardAlerts"),
  tableWrap: document.getElementById("tableWrap"),
  timelineSteps: document.getElementById("timelineSteps"),
  tableTabs: document.querySelectorAll(".tab"),
  toggleCustomRdc: document.getElementById("toggleCustomRdc"),
  customHint: document.getElementById("customHint"),
};

function setStatus(text) {
  els.status.textContent = text;
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toFixed(digits);
}

function buildPValues() {
  const maxP = Math.max(1, Math.min(8, Number(els.pStepper.value) || 3));
  const values = [];
  for (let i = 1; i <= maxP; i += 1) values.push(i);
  els.pValues.value = values.join(",");
}

function sparklineSVG(values) {
  const arr = Array.isArray(values) ? values.map((v) => Number(v) || 0) : [];
  if (!arr.length) return "";

  const w = 150;
  const h = 46;
  const minV = Math.min(...arr);
  const maxV = Math.max(...arr);
  const range = Math.max(1e-9, maxV - minV);

  const points = arr
    .map((v, i) => {
      const x = (i / Math.max(1, arr.length - 1)) * w;
      const y = h - ((v - minV) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return `<svg class="spark" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
    <polyline fill="none" stroke="#0c7973" stroke-width="2" points="${points}" />
  </svg>`;
}

function popupForStage1(point) {
  const cash = sparklineSVG(point.yearly_cashflow_10k || []);
  return `
    <div>
      <b>${point.name}</b><br/>
      城市：${point.city}<br/>
      NPV：${fmt(point.npv_10k)} 万元<br/>
      DPP：${fmt(point.dpp_years)} 年
      ${cash}
    </div>
  `;
}

function initMap() {
  if (!window.L) {
    setStatus("Leaflet未加载成功，无法显示GIS地图。");
    return;
  }

  state.map = L.map("map", {
    zoomControl: true,
    preferCanvas: true,
  }).setView([39.9042, 116.4074], 10.6);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(state.map);

  state.layers.base = L.layerGroup().addTo(state.map);
  state.layers.stage1 = L.layerGroup().addTo(state.map);
  state.layers.stage2 = L.layerGroup().addTo(state.map);
  state.layers.stage3 = L.layerGroup().addTo(state.map);
  state.layers.custom = L.layerGroup().addTo(state.map);

  state.map.on("click", onMapClickAddCustomRdc);
}

function clearLayer(layer) {
  if (layer && typeof layer.clearLayers === "function") {
    layer.clearLayers();
  }
}

function getCurrentCityConfigs() {
  const focus = els.focusCity.value;
  if (focus === "all") {
    return Object.values(state.cityConfigs || {});
  }
  return state.cityConfigs[focus] ? [state.cityConfigs[focus]] : [];
}

function updateCityParamPanel() {
  const focus = els.focusCity.value;
  const city = state.cityConfigs[focus];

  if (!city) {
    els.cityWacc.textContent = "多城市/自动";
    els.cityNpvDefault.textContent = "北京25, 杭州28";
    els.cityDppDefault.textContent = "2.5";
    return;
  }

  const p = city.params || {};
  els.cityWacc.textContent = `${fmt((p.wacc || 0) * 100, 1)}%`;
  els.cityNpvDefault.textContent = fmt(p.npv_threshold_10k, 1);
  els.cityDppDefault.textContent = fmt(p.dpp_threshold_years, 1);

  if (!els.npvThreshold.value) {
    els.npvThreshold.placeholder = `默认${fmt(p.npv_threshold_10k, 1)}`;
  }
  if (!els.dppThreshold.value) {
    els.dppThreshold.placeholder = `默认${fmt(p.dpp_threshold_years, 1)}`;
  }
}

function drawBaseCityOverlays() {
  clearLayer(state.layers.base);
  const configs = getCurrentCityConfigs();

  configs.forEach((cfg) => {
    const center = cfg.center;
    const ring = cfg.inner_ring_radius_km;

    const ringCircle = L.circle(center, {
      radius: ring * 1000,
      color: "#d14d42",
      weight: 1.5,
      fillOpacity: 0.03,
      dashArray: "4 6",
    }).bindTooltip(`${cfg.label} ${cfg.inner_ring_name}`);
    ringCircle.addTo(state.layers.base);

    (cfg.logistics_belts || []).forEach((belt) => {
      L.circle([belt.lat, belt.lon], {
        radius: (belt.radius_km || 4) * 1000,
        color: "#f2a53b",
        weight: 1,
        fillOpacity: 0.06,
      })
        .bindTooltip(`${cfg.label} - ${belt.name}`)
        .addTo(state.layers.base);
    });
  });
}

function cityMatch(value) {
  const focus = els.focusCity.value;
  if (focus === "all") return true;
  return String(value || "") === focus;
}

function fitBoundsIfAny(latlngs) {
  if (!state.map || !latlngs.length) return;
  const bounds = L.latLngBounds(latlngs);
  state.map.fitBounds(bounds.pad(0.2), { maxZoom: 13 });
}

function renderStepLayers() {
  clearLayer(state.layers.stage1);
  clearLayer(state.layers.stage2);
  clearLayer(state.layers.stage3);

  if (!state.result || !state.map) {
    drawBaseCityOverlays();
    return;
  }

  drawBaseCityOverlays();

  const points = state.result?.gis?.stage1_points || [];
  const selected = state.result?.gis?.stage2_selected || [];
  const lines = state.result?.gis?.stage3_network_lines || [];
  const openRdcs = state.result?.gis?.stage3_open_rdcs || [];

  const fit = [];

  if (state.step === "stage1") {
    points.filter((p) => cityMatch(p.city)).forEach((p) => {
      const marker = L.circleMarker([p.lat, p.lon], {
        radius: 5,
        color: p.passed ? "#1b8f5a" : "#c63f38",
        fillColor: p.passed ? "#1b8f5a" : "#c63f38",
        fillOpacity: 0.9,
        weight: 1,
      })
        .bindPopup(popupForStage1(p))
        .addTo(state.layers.stage1);
      fit.push([p.lat, p.lon]);
      marker.bringToFront();
    });
  }

  if (state.step === "stage2") {
    points.filter((p) => cityMatch(p.city)).forEach((p) => {
      L.circleMarker([p.lat, p.lon], {
        radius: 4,
        color: p.passed ? "#2c9f6a" : "#c9524a",
        fillColor: p.passed ? "#2c9f6a" : "#c9524a",
        fillOpacity: 0.45,
        weight: 1,
      }).addTo(state.layers.stage2);
      fit.push([p.lat, p.lon]);
    });

    selected.filter((s) => cityMatch(s.city)).forEach((s) => {
      L.circle([s.lat, s.lon], {
        radius: 500,
        color: "#f0a32f",
        weight: 1,
        fillOpacity: 0.05,
      }).addTo(state.layers.stage2);

      L.circle([s.lat, s.lon], {
        radius: 300,
        color: "#ce5027",
        weight: 1,
        fillOpacity: 0.08,
      }).addTo(state.layers.stage2);

      L.circleMarker([s.lat, s.lon], {
        radius: 6,
        color: "#f0a32f",
        fillColor: "#f0a32f",
        fillOpacity: 1,
      })
        .bindPopup(`<b>${s.name}</b><br/>修正NPV：${fmt(s.adjusted_npv_10k)} 万元`)
        .addTo(state.layers.stage2);
      fit.push([s.lat, s.lon]);
    });
  }

  if (state.step === "stage3") {
    openRdcs.filter((r) => cityMatch(r.city)).forEach((rdc) => {
      L.circleMarker([rdc.lat, rdc.lon], {
        radius: 7,
        color: "#0a4f9e",
        fillColor: "#2571d8",
        fillOpacity: 0.95,
      })
        .bindPopup(`<b>${rdc.name}</b><br/>${rdc.city}<br/>5年全周期成本：${fmt(rdc.lifecycle_cost_10k)} 万元`)
        .addTo(state.layers.stage3);
      fit.push([rdc.lat, rdc.lon]);
    });

    lines
      .filter((line) => cityMatch(line.store_city))
      .forEach((line) => {
        L.polyline(
          [
            [line.store_lat, line.store_lon],
            [line.rdc_lat, line.rdc_lon],
          ],
          {
            color: "#2878ff",
            weight: 1.6,
            opacity: 0.65,
          }
        )
          .bindPopup(
            `<b>${line.store_name}</b> → <b>${line.rdc_name}</b><br/>距离：${fmt(line.distance_km)} km`
          )
          .addTo(state.layers.stage3);

        L.circleMarker([line.store_lat, line.store_lon], {
          radius: 4,
          color: "#2f9a5c",
          fillColor: "#2f9a5c",
          fillOpacity: 0.8,
        }).addTo(state.layers.stage3);

        fit.push([line.store_lat, line.store_lon], [line.rdc_lat, line.rdc_lon]);
      });
  }

  // custom rdcs always visible
  clearLayer(state.layers.custom);
  state.customRdcs.forEach((rdc) => {
    L.circleMarker([rdc.lat, rdc.lon], {
      radius: 7,
      color: "#5a2ca0",
      fillColor: "#7d4ac2",
      fillOpacity: 0.9,
    })
      .bindPopup(`<b>${rdc.name}</b><br/>${rdc.city}<br/>自定义候选RDC`)
      .addTo(state.layers.custom);
    fit.push([rdc.lat, rdc.lon]);
  });

  if (!fit.length) {
    const cfg = getCurrentCityConfigs()[0];
    if (cfg) {
      state.map.setView(cfg.center, cfg.zoom || 10);
    }
  } else {
    fitBoundsIfAny(fit);
  }
}

function renderSummary() {
  const summary = state.result?.summary || {};
  const meta = state.result?.meta || {};
  const entries = [
    ["门店总量", summary.total_store_rows],
    ["阶段一通过", summary.stage1_passed],
    ["阶段二入选", summary.stage2_selected],
    ["合规RDC", summary.eligible_rdcs],
    ["最优P", summary.best_p],
    ["最优总成本(万元)", summary.best_total_cost_10k],
    ["距离来源", meta.distance_source || "-"],
    ["自定义RDC", meta.custom_rdcs || 0],
  ];

  els.summaryCards.innerHTML = entries
    .map(
      ([k, v]) => `
      <div class="kpi">
        <div class="kpi-title">${k}</div>
        <div class="kpi-value">${typeof v === "number" ? fmt(v) : v ?? "-"}</div>
      </div>
    `
    )
    .join("");
}

function renderCostBars() {
  const scenarios = state.result?.stage3?.scenarios || [];
  if (!scenarios.length) {
    els.costBars.innerHTML = "<div>暂无情景成本数据</div>";
    return;
  }

  const maxVal = Math.max(
    ...scenarios.flatMap((s) => [Number(s.rdc_cost_10k) || 0, Number(s.delivery_cost_10k) || 0]),
    1
  );

  els.costBars.innerHTML = scenarios
    .map((s) => {
      const rw = ((Number(s.rdc_cost_10k) || 0) / maxVal) * 100;
      const dw = ((Number(s.delivery_cost_10k) || 0) / maxVal) * 100;
      return `
        <div class="cost-row">
          <div>P${s.p}</div>
          <div class="track"><div class="fill-rdc" style="width:${rw}%;"></div></div>
          <div>${fmt(s.rdc_cost_10k)}</div>
        </div>
        <div class="cost-row">
          <div></div>
          <div class="track"><div class="fill-delivery" style="width:${dw}%;"></div></div>
          <div>${fmt(s.delivery_cost_10k)}</div>
        </div>
      `;
    })
    .join("");
}

function renderScenarioCards() {
  const scenarios = state.result?.stage3?.scenarios || [];
  const bestP = state.result?.stage3?.best_scenario?.p;

  if (!scenarios.length) {
    els.scenarioCards.innerHTML = "<div>暂无情景结果</div>";
    return;
  }

  els.scenarioCards.innerHTML = scenarios
    .map((s) => {
      const isBest = Number(bestP) === Number(s.p);
      return `
        <div class="scenario-card ${isBest ? "best" : ""}">
          <b>P=${s.p}</b><br/>
          总成本：${fmt(s.total_cost_10k)} 万元<br/>
          平均距离：${fmt(s.avg_distance_km)} km<br/>
          ROI：${fmt(s.roi, 3)}
        </div>
      `;
    })
    .join("");
}

function renderHardAlerts() {
  const list = [];

  (state.customViolations || []).forEach((msg) => {
    list.push(msg);
  });

  (state.result?.gis?.distance_alerts || []).forEach((a) => {
    list.push(`${a.name_a} 与 ${a.name_b} 距离 ${fmt(a.distance_m, 1)}m，不能同时开店。`);
  });

  (state.result?.stage3?.rejected_rdcs || []).forEach((r) => {
    (r.reasons || []).forEach((reason) => {
      list.push(`${r.name} 被剔除：${reason}`);
    });
  });

  if (!list.length) {
    els.hardAlerts.innerHTML = "<div>暂无硬约束告警</div>";
    return;
  }

  els.hardAlerts.innerHTML = list.slice(0, 18).map((t) => `<div class="alert">${t}</div>`).join("");
}

function buildTable(rows, columns) {
  if (!rows || !rows.length) {
    return "<p style='padding:10px;margin:0;'>暂无数据</p>";
  }

  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = rows
    .map((r) => {
      const tds = columns
        .map((c) => {
          const v = r[c.key];
          if (Array.isArray(v)) return `<td>${v.join("; ")}</td>`;
          if (typeof v === "boolean") return `<td>${v ? "是" : "否"}</td>`;
          if (typeof v === "number") return `<td>${fmt(v, 3)}</td>`;
          return `<td>${v ?? "-"}</td>`;
        })
        .join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");

  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderTableByTab() {
  if (!state.result) {
    els.tableWrap.innerHTML = "<p style='padding:10px;'>等待运行结果...</p>";
    return;
  }

  if (state.tableTab === "stage1") {
    const rows = (state.result.stage1?.rows || []).filter((r) => cityMatch(r.city));
    els.tableWrap.innerHTML = buildTable(rows, [
      { key: "store_id", label: "门店ID" },
      { key: "name", label: "门店名称" },
      { key: "city", label: "城市" },
      { key: "rf_sales_10k", label: "RF销量(万元)" },
      { key: "npv_10k", label: "NPV(万元)" },
      { key: "dpp_years", label: "DPP(年)" },
      { key: "revenue_per_sqm_10k", label: "坪效" },
      { key: "passed", label: "通过" },
      { key: "reasons", label: "原因" },
    ]);
    return;
  }

  if (state.tableTab === "stage2") {
    const rows = (state.result.stage2?.selected || []).filter((r) => cityMatch(r.city));
    els.tableWrap.innerHTML = buildTable(rows, [
      { key: "store_id", label: "门店ID" },
      { key: "name", label: "门店名称" },
      { key: "city", label: "城市" },
      { key: "base_sales_10k", label: "原始销量" },
      { key: "attenuation_ratio", label: "保留比例" },
      { key: "adjusted_sales_10k", label: "修正销量" },
      { key: "base_npv_10k", label: "原始NPV" },
      { key: "adjusted_npv_10k", label: "修正NPV" },
    ]);
    return;
  }

  const rows = (state.result.stage3?.best_scenario?.assignments || []).filter((r) => cityMatch(r.store_city));
  els.tableWrap.innerHTML = buildTable(rows, [
    { key: "store_id", label: "门店ID" },
    { key: "store_name", label: "门店" },
    { key: "store_city", label: "城市" },
    { key: "rdc_id", label: "RDC ID" },
    { key: "rdc_name", label: "RDC" },
    { key: "distance_km", label: "距离(km)" },
    { key: "delivery_cost_pv_10k", label: "配送折现成本(万元)" },
  ]);
}

function refreshAllViews() {
  updateCityParamPanel();
  renderSummary();
  renderCostBars();
  renderScenarioCards();
  renderHardAlerts();
  renderTableByTab();
  renderStepLayers();
}

async function postForm(url, formData) {
  const resp = await fetch(url, { method: "POST", body: formData });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || "request failed");
  }
  return data;
}

function createPayloadFromForm(includeFiles = true) {
  buildPValues();
  const fd = includeFiles ? new FormData(els.modelForm) : new FormData();

  if (!includeFiles) {
    [
      "focus_city",
      "max_new_stores",
      "p_values",
      "use_road_distance",
      "amap_key",
      "npv_threshold_10k",
      "dpp_threshold_years",
      "revenue_per_sqm_threshold_10k",
    ].forEach((k) => {
      const el = els.modelForm.querySelector(`[name='${k}']`);
      if (!el) return;
      if (el.type === "checkbox") {
        if (el.checked) fd.append(k, "1");
      } else {
        fd.append(k, el.value || "");
      }
    });
  }

  fd.set("p_values", els.pValues.value);
  fd.set("custom_rdcs_json", JSON.stringify(state.customRdcs));
  return fd;
}

async function runModel(url, includeFiles = true) {
  const payload = createPayloadFromForm(includeFiles);
  setStatus("模型运行中，请稍候...");
  try {
    const result = await postForm(url, payload);
    state.result = result;
    refreshAllViews();
    const info = result?.meta?.distance_source ? `\n距离来源：${result.meta.distance_source}` : "";
    setStatus(`运行成功，已更新GIS视图与看板。${info}`);
  } catch (err) {
    setStatus(`运行失败：${err.message}`);
  }
}

async function fetchCityConfigs() {
  const resp = await fetch("/api/cities");
  const data = await resp.json();
  state.cityConfigs = data.cities || {};
}

function setActiveStep(step) {
  state.step = step;
  document.querySelectorAll(".step").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.step === step);
  });
  renderStepLayers();
}

function setActiveTableTab(tab) {
  state.tableTab = tab;
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  renderTableByTab();
}

async function onMapClickAddCustomRdc(evt) {
  if (!state.customRdcMode) return;

  const focus = els.focusCity.value;
  if (focus === "all") {
    setStatus("请先切换到北京或杭州，再添加自定义RDC。");
    return;
  }

  const lat = evt.latlng.lat;
  const lon = evt.latlng.lng;

  try {
    const resp = await fetch("/api/validate-rdc-point", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city: focus, lat, lon }),
    });
    const rule = await resp.json();

    if (rule.violation) {
      const msg = `${focus === "beijing" ? "北京" : "杭州"}自定义RDC点位违规：${rule.message}`;
      state.customViolations.unshift(msg);
      state.customViolations = state.customViolations.slice(0, 8);
      renderHardAlerts();
      setStatus(msg);
      return;
    }

    const idx = state.customRdcs.length + 1;
    state.customRdcs.push({
      rdc_id: `CUSTOM_${idx}`,
      name: `自定义RDC ${idx}`,
      city: focus,
      lat,
      lon,
    });
    renderStepLayers();
    renderHardAlerts();
    setStatus(`已添加自定义RDC ${idx}（${fmt(lat, 4)}, ${fmt(lon, 4)}）`);
  } catch (err) {
    setStatus(`校验自定义RDC失败：${err.message}`);
  }
}

function bindEvents() {
  els.modelForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    await runModel("/api/run", true);
  });

  els.runSampleBtn.addEventListener("click", async () => {
    await runModel("/api/run-sample", false);
  });

  els.pStepper.addEventListener("input", buildPValues);

  els.focusCity.addEventListener("change", () => {
    updateCityParamPanel();
    renderStepLayers();
    renderTableByTab();
  });

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => setActiveStep(btn.dataset.step));
  });

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTableTab(btn.dataset.tab));
  });

  els.toggleCustomRdc.addEventListener("click", () => {
    state.customRdcMode = !state.customRdcMode;
    els.toggleCustomRdc.textContent = state.customRdcMode ? "关闭自定义RDC落点" : "开启自定义RDC落点";
    els.customHint.textContent = state.customRdcMode
      ? "自定义RDC模式已开启：点击地图添加候选点。"
      : "点击地图可添加候选RDC；若在五环/绕城内会触发红色告警";
  });
}

async function boot() {
  setStatus("正在加载城市参数与GIS底图...");
  buildPValues();
  initMap();

  try {
    await fetchCityConfigs();
    updateCityParamPanel();
    drawBaseCityOverlays();
    setStatus("系统就绪。可上传CSV运行，或直接运行样例。");
  } catch (err) {
    setStatus(`初始化失败：${err.message}`);
  }

  bindEvents();
}

boot();

// ---- AI Chat Panel ----
const chat = {
  panel: document.getElementById("chatPanel"),
  fab: document.getElementById("chatFab"),
  closeBtn: document.getElementById("chatPanelClose"),
  messages: document.getElementById("chatMessages"),
  input: document.getElementById("chatInput"),
  sendBtn: document.getElementById("chatSendBtn"),
  modelBadge: document.getElementById("chatModelBadge"),
  history: [],
  model: "",
  sessionKey: "",   // OpenClaw 会话 key，跨消息保持记忆
};

chat.fab.addEventListener("click", () => chat.panel.classList.toggle("open"));
chat.closeBtn.addEventListener("click", () => chat.panel.classList.remove("open"));

chat.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatSend();
  }
});
chat.sendBtn.addEventListener("click", chatSend);

function chatAppendMsg(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chat.messages.appendChild(div);
  chat.messages.scrollTop = chat.messages.scrollHeight;
  return div;
}

function buildSystemContext() {
  const r = state.result;
  if (!r) return "你是快乐猴选址展示系统的AI分析助手，请用中文简洁回答用户问题。当前尚无分析结果，可回答选址相关的通用问题。";

  const stage1 = r.stage1 || {};
  const stage2 = r.stage2 || {};
  const stage3 = r.stage3 || {};
  const candidates = stage1.candidates || [];
  const passCount = candidates.filter((c) => c.pass).length;
  const selectedCount = (stage2.selected_stores || []).length;

  let ctx = `你是快乐猴选址展示系统的AI分析助手，请用中文简洁回答用户问题。\n\n当前分析结果摘要：\n`;
  ctx += `- 阶段一：共 ${candidates.length} 个候选门店，${passCount} 个通过筛选，${candidates.length - passCount} 个淘汰\n`;
  ctx += `- 阶段二：从通过门店中优选出 ${selectedCount} 家新开门店\n`;

  if (stage3.scenarios && stage3.scenarios.length > 0) {
    const bestP = stage3.best_p || 1;
    const best = stage3.scenarios.find((s) => s.p === bestP) || stage3.scenarios[0];
    if (best) {
      ctx += `- 阶段三：最优 RDC 数量为 ${bestP} 个，总成本约 ${fmt(best.total_cost_10k)} 万元\n`;
    }
  }

  return ctx;
}

async function chatSend() {
  const text = chat.input.value.trim();
  if (!text || chat.sendBtn.disabled) return;

  chat.input.value = "";
  chat.sendBtn.disabled = true;
  chatAppendMsg("user", text);
  const thinking = chatAppendMsg("thinking", "思考中...");
  chat.history.push({ role: "user", content: text });

  const messages = [
    { role: "system", content: buildSystemContext() },
    ...chat.history,
  ];

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: chat.model, messages, session_key: chat.sessionKey }),
    });
    const data = await res.json();
    thinking.remove();

    if (data.error) {
      chatAppendMsg("assistant", `错误：${data.error}`);
    } else {
      const reply = data.choices?.[0]?.message?.content || "(无回复内容)";
      chat.history.push({ role: "assistant", content: reply });
      chatAppendMsg("assistant", reply);
      // 保存 session_key，下次继续同一个 OpenClaw 会话（保持记忆）
      if (data.session_key) chat.sessionKey = data.session_key;
    }
  } catch (e) {
    thinking.remove();
    chatAppendMsg("assistant", `网络错误：${e.message}`);
  }

  chat.sendBtn.disabled = false;
}

async function chatInit() {
  try {
    const res = await fetch("/api/chat/models");
    const data = await res.json();
    const models = data.data || [];
    if (models.length > 0) {
      chat.model = models[0].id;
      chat.modelBadge.textContent = `模型: ${chat.model}`;
    } else {
      chat.model = "";
      chat.modelBadge.textContent = "已连接 OpenClaw";
    }
  } catch {
    chat.modelBadge.textContent = "OpenClaw 连接异常，请检查服务";
  }
}

chatInit();
