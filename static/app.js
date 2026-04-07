const modelForm = document.getElementById("modelForm");
const runSampleBtn = document.getElementById("runSampleBtn");
const statusEl = document.getElementById("status");

function setStatus(text) {
  statusEl.textContent = text;
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toFixed(digits);
}

function keyLabel(key) {
  const map = {
    total_store_rows: "门店总记录",
    existing_stores: "存量门店",
    new_store_candidates: "新增候选",
    stage1_passed: "阶段一通过",
    stage2_selected: "阶段二入选",
    eligible_rdcs: "合规 RDC",
    best_p: "最优 P",
    best_total_cost_10k: "最优总成本(万元)",
  };
  return map[key] || key;
}

function buildTable(rows, columns) {
  if (!rows || rows.length === 0) {
    return "<p style='padding:12px;margin:0;'>暂无数据</p>";
  }

  const cols = columns || Object.keys(rows[0]).map((k) => ({ key: k, label: k }));
  const head = cols.map((c) => `<th>${c.label}</th>`).join("");

  const body = rows
    .map((row) => {
      const tds = cols
        .map((c) => {
          const raw = row[c.key];
          if (Array.isArray(raw)) {
            return `<td>${raw.join("; ")}</td>`;
          }
          if (typeof raw === "boolean") {
            return `<td>${raw ? "是" : "否"}</td>`;
          }
          if (typeof raw === "number") {
            return `<td>${fmt(raw, 3)}</td>`;
          }
          return `<td>${raw === null || raw === undefined || raw === "" ? "-" : String(raw)}</td>`;
        })
        .join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");

  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderSummary(summary) {
  const wrap = document.getElementById("summaryCards");
  wrap.innerHTML = "";
  Object.entries(summary || {}).forEach(([k, v]) => {
    const div = document.createElement("div");
    div.className = "metric";
    div.innerHTML = `
      <div class="metric-title">${keyLabel(k)}</div>
      <div class="metric-value">${typeof v === "number" ? fmt(v, 2) : v ?? "-"}</div>
    `;
    wrap.appendChild(div);
  });
}

function renderStage1(data) {
  const rows = data?.stage1?.rows || [];
  document.getElementById("stage1TableWrap").innerHTML = buildTable(rows, [
    { key: "store_id", label: "门店ID" },
    { key: "name", label: "门店名称" },
    { key: "city", label: "城市" },
    { key: "rf_sales_10k", label: "RF销量(万元)" },
    { key: "npv_10k", label: "NPV(万元)" },
    { key: "dpp_years", label: "DPP(年)" },
    { key: "revenue_per_sqm_10k", label: "坪效(万元/㎡)" },
    { key: "passed", label: "是否通过" },
    { key: "reasons", label: "未通过原因" },
  ]);
}

function renderStage2(data) {
  const stage2 = data?.stage2 || {};
  const selected = stage2.selected || [];
  document.getElementById("stage2TableWrap").innerHTML = buildTable(selected, [
    { key: "store_id", label: "门店ID" },
    { key: "name", label: "门店名称" },
    { key: "base_sales_10k", label: "原始销量(万元)" },
    { key: "attenuation_ratio", label: "保留比例" },
    { key: "adjusted_sales_10k", label: "修正销量(万元)" },
    { key: "base_npv_10k", label: "原始NPV(万元)" },
    { key: "adjusted_npv_10k", label: "修正NPV(万元)" },
    { key: "adjusted_dpp_years", label: "修正DPP(年)" },
  ]);

  const alerts = stage2.distance_alerts || [];
  const wrap = document.getElementById("distanceAlerts");
  if (!alerts.length) {
    wrap.innerHTML = "";
    return;
  }
  wrap.innerHTML = alerts
    .map(
      (a) =>
        `<div class="alert">${a.store_a} 与 ${a.store_b} 距离 ${fmt(a.distance_m, 1)}m，按规则不能同时开店。</div>`
    )
    .join("");
}

function renderStage3(data) {
  const stage3 = data?.stage3 || {};
  const scenarios = stage3.scenarios || [];

  const chartWrap = document.getElementById("scenarioChart");
  if (!scenarios.length) {
    chartWrap.innerHTML = "<p>暂无情景结果</p>";
  } else {
    const maxCost = Math.max(...scenarios.map((s) => Number(s.total_cost_10k) || 0), 1);
    chartWrap.innerHTML = scenarios
      .map((s) => {
        const widthPct = Math.max(8, (Number(s.total_cost_10k) / maxCost) * 100);
        return `
          <div class="bar-row">
            <div>P=${s.p}</div>
            <div class="bar-track"><div class="bar-fill" style="--target-width:${widthPct}%;"></div></div>
            <div>${fmt(s.total_cost_10k, 2)} 万元</div>
          </div>
        `;
      })
      .join("");
  }

  const scenarioRows = scenarios.map((s) => ({
    p: s.p,
    rdc_cost_10k: s.rdc_cost_10k,
    delivery_cost_10k: s.delivery_cost_10k,
    total_cost_10k: s.total_cost_10k,
    avg_distance_km: s.avg_distance_km,
    roi: s.roi,
    open_rdcs: (s.open_rdcs || []).map((r) => `${r.rdc_id}(${r.name})`).join(", "),
  }));

  document.getElementById("scenarioTableWrap").innerHTML = buildTable(scenarioRows, [
    { key: "p", label: "P" },
    { key: "rdc_cost_10k", label: "RDC成本(万元)" },
    { key: "delivery_cost_10k", label: "配送成本(万元)" },
    { key: "total_cost_10k", label: "总成本(万元)" },
    { key: "avg_distance_km", label: "加权平均距离(km)" },
    { key: "roi", label: "ROI" },
    { key: "open_rdcs", label: "开启RDC" },
  ]);

  const best = stage3.best_scenario || null;
  const assignments = best?.assignments || [];
  document.getElementById("assignmentTableWrap").innerHTML = buildTable(assignments, [
    { key: "store_id", label: "门店ID" },
    { key: "store_name", label: "门店名称" },
    { key: "store_city", label: "城市" },
    { key: "demand_sales_10k", label: "需求销量(万元)" },
    { key: "rdc_id", label: "RDC ID" },
    { key: "rdc_name", label: "RDC 名称" },
    { key: "distance_km", label: "距离(km)" },
    { key: "delivery_cost_pv_10k", label: "配送折现成本(万元)" },
  ]);
}

function renderAll(data) {
  renderSummary(data.summary || {});
  renderStage1(data);
  renderStage2(data);
  renderStage3(data);
}

async function runRequest(url, formData) {
  const resp = await fetch(url, { method: "POST", body: formData });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || "request failed");
  }
  return data;
}

modelForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const fd = new FormData(modelForm);
  setStatus("模型运行中，请稍候...");
  try {
    const result = await runRequest("/api/run", fd);
    renderAll(result);
    setStatus("运行成功：已更新全部阶段结果。");
  } catch (err) {
    setStatus(`运行失败：${err.message}`);
  }
});

runSampleBtn.addEventListener("click", async () => {
  const fd = new FormData();
  const maxNewStores = modelForm.querySelector("input[name='max_new_stores']")?.value || "8";
  const pValues = modelForm.querySelector("input[name='p_values']")?.value || "1,2,3";
  fd.append("max_new_stores", maxNewStores);
  fd.append("p_values", pValues);

  setStatus("样例数据运行中...");
  try {
    const result = await runRequest("/api/run-sample", fd);
    renderAll(result);
    setStatus("样例运行成功：可直接对照结果和表结构准备你的真实数据。");
  } catch (err) {
    setStatus(`样例运行失败：${err.message}`);
  }
});
