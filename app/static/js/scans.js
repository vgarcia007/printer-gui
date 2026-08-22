(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const panels = ["idlePanel", "progressPanel", "decisionPanel", "donePanel", "errorPanel"].map(id => document.getElementById(id));
  const modeButtons = [...document.querySelectorAll(".mode-card")];
  const progressTitle = document.getElementById("progressTitle");
  const progressText = document.getElementById("progressText");
  const errorText = document.getElementById("scanError");
  const retry = document.getElementById("retryOcr");
  const download = document.getElementById("downloadScan");
  const announcer = document.getElementById("scanAnnouncer");
  let mode = "document";
  let jobId = null;
  let timer = null;

  const show = id => panels.forEach(panel => { panel.hidden = panel.id !== id; });
  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf, "Content-Type": "application/json" };
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || "The scanner did not respond.");
    return data;
  };
  const apply = data => {
    jobId = data.jobId || jobId;
    const state = data.state || "idle";
    if (state === "idle" || state === "cancelled") show("idlePanel");
    else if (state === "awaiting_decision") show("decisionPanel");
    else if (state === "done") {
      show("donePanel");
      download.href = "/scans/api/files/" + encodeURIComponent(data.filename) + "/download";
      announcer.textContent = "Your searchable PDF is ready.";
    } else if (state === "error") {
      show("errorPanel");
      errorText.textContent = data.error || "The scan could not be completed.";
      retry.hidden = !data.retryAvailable;
    } else {
      show("progressPanel");
      if (state === "scanning_front") { progressTitle.textContent = "Scanning front sides…"; progressText.textContent = "The feeder will take each page automatically."; }
      else if (state === "scanning_back") { progressTitle.textContent = "Scanning back sides…"; progressText.textContent = "The feeder will take each page automatically."; }
      else { progressTitle.textContent = "Creating your searchable PDF…"; progressText.textContent = "This can take a few minutes. Temporary files are removed automatically."; }
    }
  };
  const poll = async () => {
    try { apply(await request("/scans/api/status")); }
    catch (error) { show("errorPanel"); errorText.textContent = error.message; retry.hidden = true; }
    timer = window.setTimeout(poll, 1500);
  };
  const action = async (url, body = {}) => {
    try { apply(await request(url, { method: "POST", body: JSON.stringify(body) })); }
    catch (error) { show("errorPanel"); errorText.textContent = error.message; retry.hidden = true; }
  };

  modeButtons.forEach(button => button.addEventListener("click", () => {
    mode = button.dataset.mode;
    modeButtons.forEach(item => { const selected = item === button; item.classList.toggle("selected", selected); item.setAttribute("aria-checked", String(selected)); });
  }));
  document.getElementById("scanFront").addEventListener("click", () => action("/scans/api/front", { mode }));
  document.getElementById("scanBack").addEventListener("click", () => action("/scans/api/" + jobId + "/back"));
  document.getElementById("finishFront").addEventListener("click", () => action("/scans/api/" + jobId + "/finish"));
  document.getElementById("cancelScan").addEventListener("click", () => action("/scans/api/" + jobId + "/cancel"));
  retry.addEventListener("click", () => action("/scans/api/" + jobId + "/retry-ocr"));
  document.getElementById("resetScan").addEventListener("click", () => action("/scans/api/" + jobId + "/cancel"));
  document.getElementById("newScan").addEventListener("click", () => action("/scans/api/" + jobId + "/cancel"));
  poll();
  window.addEventListener("pagehide", () => window.clearTimeout(timer));
})();
