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
          <select class="form-select drug-unit">
            ${unitOptions.map(u=>`<option value="${u}">${u}</option>`).join("")}
          </select>
        </div>
        <div class="col-12 col-sm-1">
          <input type="number" class="form-control drug-freq" placeholder="freq/day" value="${prefill.freq||1}" min="0" step="0.1">
        </div>
        <div class="col-12 col-sm-2">
          <select class="form-select drug-route">
            <option value="oral">oral</option>
            <option value="iv">iv</option>
            <option value="topical">topical</option>
          </select>
        </div>
      </div>
      <div class="small text-muted mt-1 card-note"></div>
    `;

    cardsContainer.appendChild(div);
    return div;
  }

  // Initial cards
  createCard();
  createCard();

  addCardBtn.addEventListener("click", () => createCard());

  removeCardBtn.addEventListener("click", () => {
    const cards = document.querySelectorAll(".drug-card");
    if (cards.length > 1) {
      cards[cards.length - 1].remove();
    }
  });

  pediatricToggle.addEventListener("change", () => {
    pediatricFields.style.display = pediatricToggle.checked ? "block" : "none";
  });

  predictBtn.addEventListener("click", async () => {
    resultsArea.innerHTML = "<div class='p-3 text-center'>Analyzing...</div>";

    const cards = document.querySelectorAll(".drug-card");
    const drugs = Array.from(cards).map(card => {
      return {
        name: card.querySelector(".drug-name").value.trim(),
        dose: card.querySelector(".drug-dose").value,
        unit: card.querySelector(".drug-unit").value,
        freq: card.querySelector(".drug-freq").value,
        route: card.querySelector(".drug-route").value
      };
    }).filter(d => d.name);

    if (drugs.length < 2) {
      alert("Enter at least two drugs.");
      return;
    }

    const is_pediatric = pediatricToggle.checked;
    const age = document.getElementById("patient-age").value;
    const weight_kg = document.getElementById("patient-weight").value;

    if (is_pediatric && (!weight_kg || Number(weight_kg) <= 0)) {
      alert("Pediatric mode requires weight.");
      return;
    }

    const resp = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drugs, is_pediatric, age, weight_kg })
    });

    if (!resp.ok) {
      const err = await resp.json();
      resultsArea.innerHTML = `<div class="alert alert-danger">${err.error || "Server error"}</div>`;
      return;
    }

    const data = await resp.json();
    renderResults(data);
  });

  function renderResults(data) {
    resultsArea.innerHTML = "";

    // SUMMARY CARD
    const s = data.summary;
    const summaryCard = document.createElement("div");
    summaryCard.className = "card mb-3 p-3";
    summaryCard.innerHTML = `
      <h5>Summary</h5>
      <div><strong>${s.level}</strong> — ${s.risky_pairs}/${s.total_pairs} risky pairs</div>
      <div class="small text-muted">Combined score: ${(s.combined_score * 100).toFixed(1)}%</div>
      <div class="mt-2">
        <button id="dl-csv" class="btn btn-sm btn-outline-secondary me-2">Download CSV</button>
        <button id="dl-pdf" class="btn btn-sm btn-outline-secondary">Download PDF</button>
      </div>
    `;
    resultsArea.appendChild(summaryCard);

    // PAIRWISE CARDS
    data.pairs.forEach(p => {
      const c = document.createElement("div");
      c.className = "card mb-2 p-2";

      let inner = `
        <div class="d-flex justify-content-between">
          <div><strong>${p.drug1}</strong> + <strong>${p.drug2}</strong></div>
          <div class="text-end">
            <span class="badge ${p.risk === "High" ? "bg-danger" : p.risk === "Moderate" ? "bg-warning text-dark" : "bg-success"}">
              ${p.risk}
            </span>
          </div>
        </div>

        <div class="small mt-2">
          ML prob: ${(p.prob * 100).toFixed(2)}% → adjusted: ${(p.prob_adj * 100).toFixed(2)}%
        </div>
      `;

      // Reasons
      const reasons = [];
      if (p.found) reasons.push("Known interaction in dataset");
      else if (p.prob >= 0.9) reasons.push("High ML probability");
      else if (p.prob >= 0.7) reasons.push("Moderate ML probability");
      else reasons.push("Low ML probability");

      if (p.dose_eval_a.status === "above") reasons.push("Dose A above baseline");
      if (p.dose_eval_b.status === "above") reasons.push("Dose B above baseline");

      const reasonHtml = reasons.map(r => {
        let cls = "badge-info";
        if (r.includes("High") || r.includes("above")) cls = "badge-danger";
        else if (r.includes("Moderate")) cls = "badge-warning";
        return `<span class="badge-reason ${cls}">${r}</span>`;
      }).join(" ");

      inner += `<div class="small mt-1">${reasonHtml}</div>`;

      // Dose comments
      inner += `
        <div class="small mt-2">A: ${p.dose_eval_a.comment}</div>
        <div class="small">B: ${p.dose_eval_b.comment}</div>
      `;

      // EFFECTS — (Option C: badge style)
      if (p.effects && p.effects.length > 0) {
        const effectBadge =
          p.risk === "High"
            ? "badge-danger"
            : p.risk === "Moderate"
            ? "badge-warning"
            : "badge-info";

        inner += `
          <div class="mt-3 p-2" style="background:#fafafa;border-radius:8px;">
            <div><span class="badge-reason ${effectBadge}">⚠ General Interaction Effects</span></div>
            <ul class="small mt-2 mb-0">
              ${p.effects.map(e => `<li>${e}</li>`).join("")}
            </ul>
          </div>
        `;
      }

      c.innerHTML = inner;
      resultsArea.appendChild(c);
    });

    // CSV Download
    document.getElementById("dl-csv").onclick = async () => {
      const res = await fetch("/export_csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pairs: data.pairs })
      });
      const blob = await res.blob();
      downloadBlob(blob, "ddi_results.csv");
    };

    // PDF Download
    document.getElementById("dl-pdf").onclick = async () => {
      const res = await fetch("/export_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pairs: data.pairs, summary: data.summary })
      });
      const blob = await res.blob();
      downloadBlob(blob, "ddi_report.pdf");
    };
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
});
