document.addEventListener("DOMContentLoaded", () => {
    const drugContainer = document.getElementById("drug-list-container");
    const addBtn = document.getElementById("add-drug");
    const removeBtn = document.getElementById("remove-drug");
    const predictBtn = document.getElementById("predict");
    const resultsArea = document.getElementById("results-area");
    const historyArea = document.getElementById("history-area");

    function addDrugField() {
        const div = document.createElement("div");
        div.className = "input-group mb-2";
        div.innerHTML = `<input type="text" class="form-control drug-input" placeholder="Drug name">`;
        drugContainer.appendChild(div);
    }

    function removeDrugField() {
        if (drugContainer.children.length > 1) {
            drugContainer.removeChild(drugContainer.lastElementChild);
        }
    }

    addBtn.addEventListener("click", addDrugField);
    removeBtn.addEventListener("click", removeDrugField);

    predictBtn.addEventListener("click", async () => {
        const drugs = Array.from(document.querySelectorAll(".drug-input"))
            .map(i => i.value.trim())
            .filter(Boolean);

        if (drugs.length < 2) {
            alert("Enter at least two drugs!");
            return;
        }

        resultsArea.innerHTML = "<div class='text-center p-3'>Loading...</div>";

        const response = await fetch("/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({drugs})
        });

        const data = await response.json();

        renderResults(data, drugs);
        loadHistory();
    });

    function renderResults(data, drugs) {
        resultsArea.innerHTML = "";

        const summary = data.summary;

        const summaryCard = `
            <div class="card mb-3">
              <div class="card-body">
                <h5 class="card-title">Summary</h5>
                <span class="badge-risk badge-${summary.color}">
                    ${summary.level} Risk
                </span>
                <p class="mt-2 small">Pairs with risk: ${summary.risky_pairs}/${summary.total_pairs}</p>
                <p class="small">Combined Score: ${(summary.combined_score * 100).toFixed(1)}%</p>

                <button class="btn btn-sm btn-outline-secondary me-2" id="download-csv">Download CSV</button>
                <button class="btn btn-sm btn-outline-secondary" id="download-pdf">Download PDF</button>
              </div>
            </div>
        `;

        resultsArea.insertAdjacentHTML("beforeend", summaryCard);

        data.pairs.forEach(p => {
            const card = `
                <div class="card result-card">
                  <div class="card-body">
                    <h6>${p.drug1} + ${p.drug2}</h6>
                    <span class="badge-risk badge-${p.label ? "high" : "low"}">
                        ${p.label ? "Interaction" : "Safe"}
                    </span>

                    <div class="result-description mt-2">
                        ${p.found ?
                            `📌 Known interaction: ${p.description}` :
                            `Predicted probability: ${(p.prob * 100).toFixed(2)}%`
                        }
                    </div>
                  </div>
                </div>
            `;
            resultsArea.insertAdjacentHTML("beforeend", card);
        });

        // CSV
        document.getElementById("download-csv").onclick = async () => {
            const res = await fetch("/export_csv", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({pairs: data.pairs})
            });
            const blob = await res.blob();
            downloadFile(blob, "results.csv");
        };

        // PDF
        document.getElementById("download-pdf").onclick = async () => {
            const res = await fetch("/export_pdf", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({pairs: data.pairs, summary: summary})
            });
            const blob = await res.blob();
            downloadFile(blob, "results.pdf");
        };
    }

    function downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function loadHistory() {
        const res = await fetch("/history");
        const history = await res.json();

        if (!history.length) {
            historyArea.textContent = "No history yet";
            return;
        }

        historyArea.innerHTML = history.map(h => `
            <div class="border-bottom py-2">
               <strong>${h.drugs.join(", ")}</strong><br>
               Risk: ${h.summary.level} (${(h.summary.combined_score * 100).toFixed(1)}%)
            </div>
        `).join("");
    }

    loadHistory();
});
