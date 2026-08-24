(() => {
  const t = window.appT || (message => message);
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const panels = ["idlePanel", "progressPanel", "decisionPanel", "donePanel", "errorPanel"].map(id => document.getElementById(id));
  const modeButtons = [...document.querySelectorAll(".mode-card")];
  const visual = document.getElementById("scanStatusVisual");
  const icon = document.getElementById("scanStatusIcon");
  const title = document.getElementById("scanStateTitle");
  const description = document.getElementById("scanStateText");
  const errorText = document.getElementById("scanError");
  const retry = document.getElementById("retryOcr");
  const download = document.getElementById("downloadScan");
  const announcer = document.getElementById("scanAnnouncer");
  let mode = "document";
  let jobId = null;
  let timer = null;
  let refreshedCompletion = null;

  const show = id => panels.forEach(panel => { panel.hidden = panel.id !== id; });
  const showState = (state, iconName, heading, text, spinning = false, iconStyle = "fas") => {
    visual.className = `scan-status-visual state-${state}`;
    icon.className = `${iconStyle} ${iconName} fa-fw${spinning ? " fa-spin" : ""}`;
    title.textContent = heading;
    description.textContent = text;
  };
  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf, "Content-Type": "application/json" };
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || t("The scanner did not respond."));
    return data;
  };
  const apply = data => {
    jobId = data.jobId || jobId;
    const state = data.state || "idle";
    if (state === "idle" || state === "cancelled") {
      show("idlePanel");
      showState("idle", "fa-smile", t("Ready to scan"), t("Place the pages face up, top edge first."), false, "far");
    } else if (state === "awaiting_decision") {
      show("decisionPanel");
      showState("waiting", "fa-hourglass-half", t("Waiting for rear pages"), t("Add the rear pages or finish the PDF now."));
    } else if (state === "done") {
      show("donePanel");
      showState("done", "fa-check-circle", t("Your PDF is ready"), t("The document is searchable and saved in your PDF list."), false, "far");
      download.href = "/scans/api/files/" + encodeURIComponent(data.filename) + "/download";
      announcer.textContent = t("Your searchable PDF is ready.");
      const completion = `${data.jobId || ""}:${data.filename || ""}`;
      if (completion !== refreshedCompletion) {
        refreshedCompletion = completion;
        window.ScanFiles?.refresh();
      }
    } else if (state === "error") {
      show("errorPanel");
      showState("error", "fa-frown-open", t("That did not work"), t("Nothing was lost. Check the message below and try again."), false, "far");
      errorText.textContent = data.error || t("The scan could not be completed.");
      retry.hidden = !data.retryAvailable;
    } else if (state === "scanning_front") {
      show("progressPanel");
      showState("scanning", "fa-spinner", t("Scan in progress"), t("The feeder is taking each page automatically."), true);
    } else if (state === "scanning_back") {
      show("progressPanel");
      showState("scanning", "fa-spinner", t("Scan in progress"), t("The feeder is taking each page automatically."), true);
    } else {
      show("progressPanel");
      showState("ocr", "fa-brain", t("OCR in progress"), t("OCR can take a moment. Temporary files are removed automatically."));
    }
  };
  const showRequestError = error => {
    show("errorPanel");
    showState("error", "fa-frown-open", t("Scanner unavailable"), t("The scanner did not answer."), false, "far");
    errorText.textContent = error.message;
    retry.hidden = true;
  };
  const poll = async () => {
    try { apply(await request("/scans/api/status")); }
    catch (error) { showRequestError(error); }
    timer = window.setTimeout(poll, 1500);
  };
  const action = async (url, body = {}) => {
    try { apply(await request(url, { method: "POST", body: JSON.stringify(body) })); }
    catch (error) { showRequestError(error); }
  };

  modeButtons.forEach(button => button.addEventListener("click", () => {
    mode = button.dataset.mode;
    modeButtons.forEach(item => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-checked", String(selected));
    });
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
