// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  const cardsContainer = document.getElementById("cards-container");
  const addCardBtn = document.getElementById("add-card");
  const removeCardBtn = document.getElementById("remove-card");
  const predictBtn = document.getElementById("predict");
  const pediatricToggle = document.getElementById("pediatric-toggle");
  const pediatricFields = document.getElementById("pediatric-fields");
  const historyArea = document.getElementById("history-area");
  const resultsArea = document.getElementById("results-area");
  const columnHeadings = document.getElementById("column-headings");

  const unitOptions = ["mg","g","mL","mcg","IU"];

  function createCard(prefill={}) {
    if (columnHeadings.style.display === "none") columnHeadings.style.display = "flex";
    const div = document.createElement("div");
    div.className = "card mb-2 p-2 drug-card";
    div.innerHTML = `
      <div class="row g-2 align-items-center">
        <div class="col-12 col-sm-5">
          <input type="text" class="form-control drug-name" placeholder="Drug name" value="${prefill.name||""}">
        </div>
        <div class="col-12 col-sm-2">
          <input type="number" class="form-control drug-dose" placeholder="Dose" value="${prefill.dose||""}" step="0.1" min="0">
        </div>
        <div class="col-12 col-sm-2">
          <select class="form-select drug-unit">${unitOptions.map(u=>`<option value="${u}">${u}</option>`).join("")}</select>
        </div>
        <div class="col-12 col-sm-1">
          <input type="number" class="form-control drug-freq" placeholder="freq/day" value="${prefill.freq||1}" min="0" step="0.1">
        </div>
        <div class="col-12 col-sm-2">
          <select class="form-select drug-route">
            <option value="oral">oral</option><option value="iv">iv</option><option value="topical">topical</option>
          </select>
        </div>
      </div>
      <div class="small text-muted mt-1 card-note"></div>
    `;
    cardsContainer.appendChild(div);
    return div;
  }

  // init with 2 cards
  createCard(); createCard();

  addCardBtn.addEventListener("click", ()=> createCard());
  removeCardBtn.addEventListener("click", ()=>{
    const cards = document.querySelectorAll(".drug-card");
    if (cards.length > 1) cards[cards.length-1].remove();
    if (document.querySelectorAll(".drug-card").length === 0) columnHeadings.style.display = "none";
  });

  pediatricToggle.addEventListener("change", (e)=>{
    pediatricFields.style.display = e.target.checked ? "block" : "none";
  });

  async function loadHistory(){
    try {
      const res = await fetch("/history");
      const h = await res.json();
      if(!h || h.length===0){
        historyArea.innerHTML = "<div class='text-muted small'>No recent checks</div>"; return;
      }
      historyArea.innerHTML = h.slice(0,6).map(item=>{
        return `<div class="mb-1"><strong>${item.drugs.join(", ")}</strong><br><small class="text-muted">${item.summary.level} (${(item.summary.combined_score*100).toFixed(1)}%)</small></div>`;
      }).join("");
    } catch(e) {
      historyArea.innerHTML = "<div class='text-muted small'>History unavailable</div>";
    }
  }

  predictBtn.addEventListener("click", async ()=>{
    resultsArea.innerHTML = "<div class='p-3 text-center'>Analyzing...</div>";
    const cards = document.querySelectorAll(".drug-card");
    const drugs = Array.from(cards).map(c=>{
      const name = c.querySelector(".drug-name").value.trim();
      const dose = c.querySelector(".drug-dose").value;
      const unit = c.querySelector(".drug-unit").value;
      const freq = c.querySelector(".drug-freq").value;
      const route = c.querySelector(".drug-route").value;
      return {name, dose, unit, freq, route};
    }).filter(x=>x.name);

    const is_pediatric = pediatricToggle.checked;
    const age = document.getElementById("patient-age") ? document.getElementById("patient-age").value : null;
    const weight_kg = document.getElementById("patient-weight") ? document.getElementById("patient-weight").value : null;
    if (is_pediatric && (!weight_kg || Number(weight_kg)<=0)) {
      alert("Pediatric mode requires patient weight (kg)."); return;
    }

    if (drugs.length < 2) { alert("Enter at least two drugs"); return; }

    const resp = await fetch("/predict", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({drugs, is_pediatric, age, weight_kg})
    });

    if (!resp.ok) {
      const err = await resp.json();
      resultsArea.innerHTML = `<div class="alert alert-danger">${err.error || "Server error"}</div>`;
      return;
    }

    const data = await resp.json();
    renderResults(data, drugs);
    loadHistory();
  });

  function renderResults(data, drugs) {
    resultsArea.innerHTML = "";

    const s = data.summary;
    const header = document.createElement("div");
    header.className = "card mb-3 p-3";
    header.innerHTML = `<h5>Summary</h5>
      <div><strong>${s.level}</strong> — ${s.risky_pairs}/${s.total_pairs} risky pairs</div>
      <div class="small text-muted">Combined score: ${(s.combined_score*100).toFixed(1)}%</div>
      <div class="mt-2">
        <button id="dl-csv" class="btn btn-sm btn-outline-secondary me-2">Download CSV</button>
        <button id="dl-pdf" class="btn btn-sm btn-outline-secondary">Download PDF</button>
      </div>
    `;
    resultsArea.appendChild(header);

    // For each pair: show short + dosage reason (Q2: C)
    data.pairs.forEach(p=>{
      const card = document.createElement("div");
      card.className = "card mb-2 p-2";
      // prepare reasons array
      const reasons = [];
      if (p.found) reasons.push("Known interaction in dataset");
      else {
        if (p.prob >= 0.9) reasons.push("High ML probability");
        else if (p.prob >= 0.7) reasons.push("Moderate ML probability");
        else reasons.push("Low ML probability");
      }
      // dosage info (informational only)
      const aComment = p.dose_eval_a && p.dose_eval_a.comment ? p.dose_eval_a.comment : "";
      const bComment = p.dose_eval_b && p.dose_eval_b.comment ? p.dose_eval_b.comment : "";
      if (aComment && aComment.toLowerCase().indexOf("above")>=0) reasons.push("Dose A above baseline");
      if (bComment && bComment.toLowerCase().indexOf("above")>=0) reasons.push("Dose B above baseline");

      const reasonHtml = reasons.map(r=>{
        let cls = "badge-info";
        if (r.toLowerCase().includes("high") || r.toLowerCase().includes("above")) cls = "badge-danger";
        else if (r.toLowerCase().includes("moderate")) cls = "badge-warning";
        return `<span class="badge-reason ${cls}">${r}</span>`;
      }).join(" ");

      card.innerHTML = `<div class="d-flex justify-content-between">
          <div><strong>${p.drug1}</strong> + <strong>${p.drug2}</strong></div>
          <div class="text-end"><span class="badge ${p.risk==='High'?'bg-danger':(p.risk==='Moderate'?'bg-warning text-dark':'bg-success')}">${p.risk}</span></div>
        </div>
        <div class="small mt-2">
          <div>ML prob: ${(p.prob*100).toFixed(2)}% → adjusted: ${(p.prob_adj*100).toFixed(2)}%</div>
          <div class="mt-1">${reasonHtml}</div>
          <div class="mt-2">A: ${aComment || "No baseline dosing info available"}</div>
          <div>B: ${bComment || "No baseline dosing info available"}</div>
        </div>`;
      resultsArea.appendChild(card);
    });

    document.getElementById("dl-csv").onclick = async () => {
      const res = await fetch("/export_csv", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({pairs: data.pairs})
      });
      const blob = await res.blob(); downloadBlob(blob, "ddi_results.csv");
    };
    document.getElementById("dl-pdf").onclick = async () => {
      const res = await fetch("/export_pdf", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({pairs: data.pairs, summary: data.summary})
      });
      const blob = await res.blob(); downloadBlob(blob, "ddi_report.pdf");
    };
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  loadHistory();
});
