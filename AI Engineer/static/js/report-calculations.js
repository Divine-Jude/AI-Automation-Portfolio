/**
 * Live metrics + JSON sync (mirrors calculations.py).
 */
(function () {
  const cfg = window.__AW_REPORT__;
  if (!cfg) return;

  const money = (n) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(n) || 0);

  function parseJSON(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  }

  function retirementTotal(obj) {
    return Object.values(obj || {}).reduce((s, v) => s + (parseFloat(v) || 0), 0);
  }

  function nonRetTotal(arr) {
    return (arr || []).reduce((s, r) => s + (parseFloat(r.balance) || 0), 0);
  }

  function liabSum(arr) {
    return (arr || []).reduce((s, r) => s + (parseFloat(r.balance) || 0), 0);
  }

  function computeMetrics() {
    const inflow = parseFloat(document.querySelector('[name="inflow"]')?.value) || 0;
    const outflow = parseFloat(document.querySelector('[name="outflow"]')?.value) || 0;
    const trust = parseFloat(document.querySelector('[name="trust_zillow_value"]')?.value) || 0;
    const monthlyExp = cfg.monthlyExpense || 0;
    const insuranceDed = cfg.insuranceDed || 0;

    let c1 = {};
    let c2 = {};
    let nonRet = [];
    let liabs = [];
    try {
      c1 = JSON.parse(document.getElementById("retirement_c1_json").value || "{}");
    } catch {
      c1 = {};
    }
    try {
      c2 = JSON.parse(document.getElementById("retirement_c2_json").value || "{}");
    } catch {
      c2 = {};
    }
    try {
      nonRet = JSON.parse(document.getElementById("non_retirement_json").value || "[]");
    } catch {
      nonRet = [];
    }
    try {
      liabs = JSON.parse(document.getElementById("liabilities_json").value || "[]");
    } catch {
      liabs = [];
    }

    const excess = inflow - outflow;
    const privateReserveTarget = monthlyExp * 6 + insuranceDed;
    const c1r = retirementTotal(c1);
    const c2r = retirementTotal(c2);
    const nr = nonRetTotal(nonRet);
    const grand = c1r + c2r + nr + trust;
    const lsum = liabSum(liabs);

    return {
      excess,
      private_reserve_target: privateReserveTarget,
      client1_retirement_total: c1r,
      client2_retirement_total: c2r,
      non_retirement_total: nr,
      grand_total_net_worth: grand,
      liabilities_total: lsum,
    };
  }

  function syncHiddenFromUI() {
    document.getElementById("retirement_c1_json").value = JSON.stringify(collectRetirement("c1"));
    document.getElementById("retirement_c2_json").value = JSON.stringify(collectRetirement("c2"));
    document.getElementById("non_retirement_json").value = JSON.stringify(collectNonRet());
    document.getElementById("liabilities_json").value = JSON.stringify(collectLiabs());
  }

  function collectRetirement(which) {
    const root = document.getElementById(which === "c1" ? "ret-c1-rows" : "ret-c2-rows");
    const out = {};
    if (!root) return out;
    root.querySelectorAll("[data-ret-row]").forEach((row) => {
      const name = row.querySelector(".ret-name")?.value?.trim();
      const bal = row.querySelector(".ret-bal")?.value;
      if (name) out[name] = bal === "" ? "0" : String(bal);
    });
    return out;
  }

  function collectNonRet() {
    const root = document.getElementById("non-ret-rows");
    const out = [];
    root.querySelectorAll("[data-non-row]").forEach((row) => {
      const name = row.querySelector(".non-name")?.value?.trim();
      const bal = row.querySelector(".non-bal")?.value;
      if (name) out.push({ name, balance: bal === "" ? "0" : String(bal) });
    });
    return out;
  }

  function collectLiabs() {
    const root = document.getElementById("liab-rows");
    const out = [];
    root.querySelectorAll("[data-liab-row]").forEach((row) => {
      const name = row.querySelector(".liab-name")?.value?.trim();
      const bal = row.querySelector(".liab-bal")?.value;
      const rate = row.querySelector(".liab-rate")?.value;
      if (name)
        out.push({
          name,
          balance: bal === "" ? "0" : String(bal),
          rate: rate === "" ? "0" : String(rate),
        });
    });
    return out;
  }

  function retRow(name, bal) {
    const wrap = document.createElement("div");
    wrap.setAttribute("data-ret-row", "1");
    wrap.className = "flex flex-wrap items-end gap-2 rounded-lg bg-slate-50 p-2";
    wrap.innerHTML = `
      <div class="min-w-[140px] flex-1">
        <label class="text-xs text-slate-600">Account</label>
        <input type="text" class="ret-name mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${name || ""}" />
      </div>
      <div class="w-36">
        <label class="text-xs text-slate-600">Balance</label>
        <input type="number" step="0.01" class="ret-bal mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${bal ?? ""}" />
      </div>
      <button type="button" class="mb-0.5 rounded bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300" data-remove>Remove</button>
    `;
    wrap.querySelector("[data-remove]").addEventListener("click", () => {
      wrap.remove();
      onFieldChange();
    });
    wrap.querySelectorAll("input").forEach((i) => i.addEventListener("input", onFieldChange));
    return wrap;
  }

  function nonRow(name, bal) {
    const wrap = document.createElement("div");
    wrap.setAttribute("data-non-row", "1");
    wrap.className = "flex flex-wrap items-end gap-2 rounded-lg bg-slate-50 p-2";
    wrap.innerHTML = `
      <div class="min-w-[140px] flex-1">
        <label class="text-xs text-slate-600">Account</label>
        <input type="text" class="non-name mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${name || ""}" />
      </div>
      <div class="w-36">
        <label class="text-xs text-slate-600">Balance</label>
        <input type="number" step="0.01" class="non-bal mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${bal ?? ""}" />
      </div>
      <button type="button" class="mb-0.5 rounded bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300" data-remove>Remove</button>
    `;
    wrap.querySelector("[data-remove]").addEventListener("click", () => {
      wrap.remove();
      onFieldChange();
    });
    wrap.querySelectorAll("input").forEach((i) => i.addEventListener("input", onFieldChange));
    return wrap;
  }

  function liabRow(name, bal, rate) {
    const wrap = document.createElement("div");
    wrap.setAttribute("data-liab-row", "1");
    wrap.className = "flex flex-wrap items-end gap-2 rounded-lg bg-slate-50 p-2";
    wrap.innerHTML = `
      <div class="min-w-[120px] flex-1">
        <label class="text-xs text-slate-600">Name</label>
        <input type="text" class="liab-name mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${name || ""}" />
      </div>
      <div class="w-32">
        <label class="text-xs text-slate-600">Balance</label>
        <input type="number" step="0.01" class="liab-bal mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${bal ?? ""}" />
      </div>
      <div class="w-24">
        <label class="text-xs text-slate-600">Rate %</label>
        <input type="number" step="0.01" class="liab-rate mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" value="${rate ?? ""}" />
      </div>
      <button type="button" class="mb-0.5 rounded bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300" data-remove>Remove</button>
    `;
    wrap.querySelector("[data-remove]").addEventListener("click", () => {
      wrap.remove();
      onFieldChange();
    });
    wrap.querySelectorAll("input").forEach((i) => i.addEventListener("input", onFieldChange));
    return wrap;
  }

  function hydrateRetirement(which, data) {
    const root = document.getElementById(which === "c1" ? "ret-c1-rows" : "ret-c2-rows");
    root.innerHTML = "";
    const obj = typeof data === "object" && data ? data : {};
    const keys = Object.keys(obj);
    if (keys.length === 0) {
      root.appendChild(retRow("", ""));
      return;
    }
    keys.forEach((k) => root.appendChild(retRow(k, obj[k])));
  }

  function hydrateNonRet(arr) {
    const root = document.getElementById("non-ret-rows");
    root.innerHTML = "";
    if (!arr || !arr.length) {
      root.appendChild(nonRow("", ""));
      return;
    }
    arr.forEach((r) => root.appendChild(nonRow(r.name, r.balance)));
  }

  function hydrateLiabs(arr) {
    const root = document.getElementById("liab-rows");
    root.innerHTML = "";
    if (!arr || !arr.length) {
      root.appendChild(liabRow("", "", ""));
      return;
    }
    arr.forEach((r) => root.appendChild(liabRow(r.name, r.balance, r.rate)));
  }

  let debounceTimer;
  function onFieldChange() {
    syncHiddenFromUI();
    const m = computeMetrics();
    updateLocalPreview(m);
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const form = document.getElementById("report-form");
      if (form && window.htmx) {
        htmx.ajax("POST", cfg.previewUrl, { source: form, target: "#calc-preview", swap: "innerHTML" });
      }
    }, 450);
  }

  function updateLocalPreview(m) {
    const el = document.getElementById("calc-preview");
    if (!el) return;
    el.querySelectorAll("[data-metric]").forEach((b) => {
      const k = b.getAttribute("data-metric");
      if (m[k] !== undefined) b.textContent = money(m[k]);
    });
  }

  // --- init ---
  hydrateRetirement("c1", parseJSON("seed-ret-c1", {}));
  if (cfg.isMarried) hydrateRetirement("c2", parseJSON("seed-ret-c2", {}));
  else {
    const r2 = document.getElementById("ret-c2-rows");
    if (r2) {
      r2.innerHTML = "";
      document.getElementById("retirement_c2_json").value = "{}";
    }
  }
  hydrateNonRet(parseJSON("seed-non-ret", []));
  hydrateLiabs(parseJSON("seed-liab", []));

  syncHiddenFromUI();

  document.querySelectorAll("[data-add-ret]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const which = btn.getAttribute("data-add-ret");
      document.getElementById(which === "c1" ? "ret-c1-rows" : "ret-c2-rows").appendChild(retRow("", ""));
      onFieldChange();
    });
  });
  document.getElementById("add-non-ret")?.addEventListener("click", () => {
    document.getElementById("non-ret-rows").appendChild(nonRow("", ""));
    onFieldChange();
  });
  document.getElementById("add-liab")?.addEventListener("click", () => {
    document.getElementById("liab-rows").appendChild(liabRow("", "", ""));
    onFieldChange();
  });

  document.getElementById("report-form")?.addEventListener("input", onFieldChange);
  document.getElementById("report-form")?.addEventListener("change", onFieldChange);

  // Add data-metric hooks to server-rendered preview for instant local updates
  (function tagPreview() {
    const root = document.getElementById("calc-preview");
    if (!root) return;
    const bigs = root.querySelectorAll(".text-2xl.font-bold, .text-xl.font-semibold");
    // Order matches partial: 0 excess, 1 target, 2 c1, 3 c2, 4 nonret, 5 grand, 6 liab
    const order = [
      "excess",
      "private_reserve_target",
      "client1_retirement_total",
      "client2_retirement_total",
      "non_retirement_total",
      "grand_total_net_worth",
      "liabilities_total",
    ];
    bigs.forEach((el, i) => {
      if (order[i]) el.setAttribute("data-metric", order[i]);
    });
  })();

  onFieldChange();
})();
