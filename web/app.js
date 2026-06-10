/* Phase 1 dashboard — vanilla JS, talks to serve.py's JSON API. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const LANES = ["safe", "early", "whitespace"];
const LANE_LABEL = { safe: "🟢 Safe", early: "🟡 Early", whitespace: "🔵 Whitespace" };

const state = { data: null, ledger: null, lane: "all" };
/* Static snapshot mode: tools/export_static.py embeds the run data so the
   page works with no server (GitHub Pages, file://, htmlpreview). */
const STATIC = Boolean(window.__ENGINE_DATA__);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const money = (n) => "$" + Number(n).toFixed(2);
const pct = (n) => (Number(n) * 100).toFixed(1) + "%";

async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `${url} -> HTTP ${res.status}`);
  return body;
}

/* ---------- run form ---------- */

async function initForm() {
  const cfg = await getJSON("/api/config");
  $("#seeds").value = cfg.defaults.seeds;
  $("#cats").innerHTML = cfg.categories.map((c, i) =>
    `<label><input type="checkbox" value="${esc(c)}" ${i < 2 ? "checked" : ""}>${esc(c)}</label>`
  ).join("");
  $("#persona").innerHTML = cfg.personas.map((p) =>
    `<option value="${esc(p)}">${esc(p)}</option>`).join("");
}

async function runEngine() {
  const btn = $("#runBtn"), status = $("#runStatus");
  btn.disabled = true;
  status.className = "status";
  status.textContent = "running scouts → fan-out → filter → economics → fusion…";
  try {
    const payload = {
      seeds: $("#seeds").value,
      categories: [...document.querySelectorAll("#cats input:checked")].map((x) => x.value),
      persona: $("#persona").value,
      price_min: $("#priceMin").value,
      price_max: $("#priceMax").value,
      proven_mode: $("#provenMode").value,
      ai: $("#aiBackend").value,
      exclude: $("#exclude").value,
    };
    state.data = await getJSON("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.ledger = null;                      // stale now; refetched on tab open
    status.textContent = `run ${state.data.run_id} done — ${state.data.total_ranked} ranked`;
    renderAll();
    if ($("#ledger").hidden === false) loadLedger();
  } catch (e) {
    status.className = "status err";
    status.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

/* ---------- rendering ---------- */

function renderAll() {
  renderMeta();
  renderGuardrails();
  renderLaneChips();
  renderTable();
}

function renderMeta() {
  const d = state.data;
  if (!d) { $("#runMeta").innerHTML = ""; return; }
  const mock = d.connector === "mock";
  $("#runMeta").innerHTML = `
    <span class="badge">run ${esc(d.run_id)}</span>
    <span class="badge">persona ${esc(d.ctx.persona)}</span>
    <span class="badge">ai ${esc(d.ai_backend)}</span>
    <span class="badge ${mock ? "warn" : ""}">${mock ? "⚠ MOCK DATA" : "live data"}</span>`;
}

function renderGuardrails() {
  const d = state.data;
  if (!d) { $("#guardrails").innerHTML = ""; return; }
  const g = d.guardrails, budget = g.G1_budget || {};
  const bars = Object.entries(budget).map(([r, b]) => {
    const used = b.cap ? Math.min(100, (b.spent / b.cap) * 100) : 0;
    return `<div class="sub2">${esc(r)} ${b.spent}/${b.cap ?? "∞"}${b.denied ? " · denied " + b.denied : ""}</div>
            <div class="bar"><i class="${used >= 100 ? "full" : ""}" style="width:${used}%"></i></div>`;
  }).join("");
  $("#guardrails").innerHTML = `
    <div class="gcard"><div class="k">G1 · budget</div>${bars}</div>
    <div class="gcard"><div class="k">G2 · data source</div>
      <div class="v ${d.connector === "mock" ? "warn" : ""}">${d.connector === "mock" ? "mock" : "live"}</div>
      <div class="sub2">${esc(String(g.G2_data))}</div></div>
    <div class="gcard"><div class="k">G3 · size/compliance marks</div>
      <div class="v">${g.G3_size_or_compliance_marked}</div><div class="sub2">marked, never silently dropped</div></div>
    <div class="gcard"><div class="k">G4 · below margin floor</div>
      <div class="v ${g.G4_below_margin_floor ? "warn" : ""}">${g.G4_below_margin_floor}</div>
      <div class="sub2">in shortlist</div></div>
    <div class="gcard"><div class="k">G5 · saturated</div>
      <div class="v ${g.G5_saturated_in_shortlist ? "warn" : ""}">${g.G5_saturated_in_shortlist}</div>
      <div class="sub2">in shortlist</div></div>`;
}

function renderLaneChips() {
  const counts = { all: 0, safe: 0, early: 0, whitespace: 0 };
  (state.data?.candidates || []).forEach((c) => { counts.all++; counts[c.lane]++; });
  $("#laneChips").innerHTML = ["all", ...LANES].map((l) =>
    `<button class="chip ${state.lane === l ? "active" : ""}" data-lane="${l}">
       ${l === "all" ? "All" : LANE_LABEL[l]} (${counts[l]})</button>`).join("");
  document.querySelectorAll(".chip").forEach((ch) =>
    ch.addEventListener("click", () => { state.lane = ch.dataset.lane; renderLaneChips(); renderTable(); }));
}

function renderTable() {
  const tbody = $("#candTable tbody");
  const cands = (state.data?.candidates || [])
    .filter((c) => state.lane === "all" || c.lane === state.lane);
  $("#empty").hidden = Boolean(state.data);
  tbody.innerHTML = cands.map((c, i) => {
    const e = c.economics, r = c.raw;
    return `<tr data-asin="${esc(c.asin)}">
      <td>${i + 1}</td>
      <td><span class="lane ${c.lane}">${LANE_LABEL[c.lane]}</span></td>
      <td title="${esc(r.title)}">${esc(r.title.slice(0, 52))}<div class="prov">${esc(c.asin)} · ${esc(r.category)} · ${esc(r.trend)}</div></td>
      <td class="num">${money(r.price)}</td>
      <td class="num">${e.units_per_month}</td>
      <td class="num">${money(e.revenue_per_month)}</td>
      <td class="num">${pct(e.margin_pct)}</td>
      <td class="num">${c.score}<span class="scorebar"><i style="width:${Math.min(100, c.score)}%"></i></span></td>
      <td>${c.marks.map((m) => `<span class="mark">${esc(m)}</span>`).join("") || "—"}</td>
    </tr>`;
  }).join("");
  tbody.querySelectorAll("tr").forEach((tr) =>
    tr.addEventListener("click", () => openDrawer(tr.dataset.asin)));
}

function openDrawer(asin) {
  const c = (state.data?.candidates || []).find((x) => x.asin === asin);
  if (!c) return;
  const e = c.economics, r = c.raw;
  const sbars = Object.entries(c.sub_scores).map(([k, v]) => `
    <div class="sbar"><div class="lab"><span>${esc(k)}</span><span>${v}</span></div>
    <div class="track"><i style="width:${Math.min(100, v)}%"></i></div></div>`).join("");
  $("#drawerBody").innerHTML = `
    <h2>${esc(r.title)}</h2>
    <span class="lane ${c.lane}">${LANE_LABEL[c.lane]}</span> · score <b>${c.score}</b> · origin ${esc(c.origin)}
    ${c.rationale ? `<div class="rationale">${esc(c.rationale)}</div>` : ""}
    ${c.compliance_notes.map((n) =>
      `<div class="compliance">⚠ <b>${esc(n.mark)}</b> (${esc(n.risk)} risk) — ${esc(n.action)}</div>`).join("")}
    <h3>Sub-scores</h3>${sbars}
    <h3>Economics (est.)</h3>
    <div class="kv">
      <span class="k">price</span><span>${money(r.price)}</span>
      <span class="k">units / mo</span><span>${e.units_per_month}</span>
      <span class="k">revenue / mo</span><span>${money(e.revenue_per_month)}</span>
      <span class="k">referral fee</span><span>${money(e.referral_fee)}</span>
      <span class="k">FBA fee</span><span>${money(e.fba_fee)}</span>
      <span class="k">landed (assumed)</span><span>${money(e.landed_cost_est)}</span>
      <span class="k">net margin</span><span><b>${pct(e.margin_pct)}</b></span>
      <span class="k">breakeven price</span><span>${money(e.breakeven_price)}</span>
      <span class="k">FBA ready</span><span>${e.fba_ready ? "✅" : "❌ (score capped)"}</span>
    </div>
    <h3>Market snapshot</h3>
    <div class="kv">
      <span class="k">BSR</span><span>${r.bsr}</span>
      <span class="k">trend</span><span>${esc(r.trend)}</span>
      <span class="k">rating</span><span>${r.rating}★ · ${r.reviews_count} reviews</span>
      <span class="k">sellers</span><span>${r.sellers_count}</span>
      <span class="k">weight</span><span>${r.weight_oz} oz</span>
    </div>
    <h3>Provenance — found by</h3>
    <div class="prov">${r.found_by.map((f) => `<code>${esc(f)}</code>`).join("")}</div>`;
  $("#drawer").hidden = false;
}

/* ---------- ledger tab ---------- */

async function loadLedger() {
  try {
    if (!state.ledger) {
      state.ledger = STATIC ? (window.__ENGINE_LEDGER__ || [])
                            : (await getJSON("/api/ledger")).events;
    }
  } catch (e) {
    $("#ledgerSummary").innerHTML = `<span class="badge warn">${esc(e.message)}</span>`;
    return;
  }
  const ev = state.ledger;
  const counts = {};
  ev.forEach((x) => { counts[x.kind] = (counts[x.kind] || 0) + 1; });
  $("#ledgerSummary").innerHTML = Object.entries(counts).map(([k, n]) =>
    `<span class="badge">${esc(k)} × ${n}</span>`).join("");
  $("#dropTable tbody").innerHTML = ev.filter((x) => x.kind === "candidate_dropped")
    .slice(0, 60).map((x) => `<tr>
      <td>${esc(x.asin)}</td><td>${esc(x.title)}</td>
      <td class="num">${money(x.price)}</td><td><span class="mark">${esc(x.reason)}</span></td></tr>`)
    .join("") || `<tr><td colspan="4">no drops this run</td></tr>`;
  $("#seamTable tbody").innerHTML = ev.filter((x) => x.kind === "ai_seam")
    .map((x) => `<tr><td>${esc(x.seam)}</td><td>${esc(x.backend)}</td>
      <td class="prov">${esc((x.result_summary || "").slice(0, 160))}</td></tr>`)
    .join("") || `<tr><td colspan="3">none</td></tr>`;
}

/* ---------- wiring ---------- */

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
  const ledger = t.dataset.tab === "ledger";
  $("#results").hidden = ledger;
  $("#ledger").hidden = !ledger;
  if (ledger) loadLedger();
}));
$("#runBtn").addEventListener("click", runEngine);
$("#drawerClose").addEventListener("click", () => { $("#drawer").hidden = true; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#drawer").hidden = true; });

(async function init() {
  if (STATIC) {
    state.data = window.__ENGINE_DATA__;
    const ctx = state.data.ctx || {};
    $("#seeds").value = (ctx.seeds || []).join(", ");
    $("#persona").innerHTML = `<option>${esc(ctx.persona || "default")}</option>`;
    $("#cats").innerHTML = (ctx.categories || []).map((c) =>
      `<label><input type="checkbox" checked disabled>${esc(c)}</label>`).join("");
    $("#runPanel").querySelectorAll("input, select, textarea, #runBtn")
      .forEach((el) => { el.disabled = true; });
    $("#runStatus").textContent =
      "static snapshot — clone the repo and run `python3 serve.py` for live runs";
    renderAll();
    return;
  }
  try { await initForm(); } catch (e) { $("#runStatus").textContent = e.message; }
  try {
    state.data = await getJSON("/api/shortlist");
    renderAll();
  } catch {
    $("#empty").hidden = false;          // no run yet — that's fine
  }
})();
