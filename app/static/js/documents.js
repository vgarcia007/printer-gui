(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const printer = document.getElementById("printer");
  const jobsHint = document.getElementById("jobsHint");
  const printJobs = document.getElementById("printJobs");
  const dropZone = document.getElementById("dropZone");
  const input = document.getElementById("fileInput");
  const card = document.getElementById("fileCard");
  const name = document.getElementById("fileName");
  const size = document.getElementById("fileSize");
  const remove = document.getElementById("removeFile");
  const printFile = document.getElementById("printFile");
  const status = document.getElementById("documentStatus");
  let selectedFile = null;

  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf };
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) throw new Error(payload.error || "The request could not be completed.");
    return payload;
  };
  const busy = value => {
    printJobs.disabled = value || Number(printJobs.dataset.count || 0) < 1 || !printer.value;
    printFile.disabled = value || !selectedFile || !printer.value;
    printer.disabled = value;
  };
  const setFile = file => {
    if (file && !file.name.toLowerCase().endsWith(".pdf")) {
      status.textContent = "Please choose a PDF file.";
      return;
    }
    selectedFile = file || null;
    card.hidden = !selectedFile;
    dropZone.hidden = Boolean(selectedFile);
    if (selectedFile) {
      name.textContent = selectedFile.name;
      size.textContent = (selectedFile.size / 1024 / 1024).toFixed(1) + " MB";
    }
    busy(false);
  };
  const load = async () => {
    try {
      const data = await request("/documents/api/status");
      printer.replaceChildren();
      for (const item of data.printers) {
        const option = document.createElement("option");
        option.value = item.name;
        option.textContent = item.ready ? item.label : item.label + " — check printer";
        option.selected = item.name === data.defaultPrinter;
        printer.append(option);
      }
      if (!data.printers.length) {
        const option = document.createElement("option");
        option.textContent = "No document printer available";
        printer.append(option);
      }
      printJobs.dataset.count = data.jobCount;
      jobsHint.textContent = data.jobCount === 1 ? "1 PDF is waiting." : data.jobCount + " PDFs are waiting.";
      status.textContent = data.printers.length ? "Ready." : "No configured document printer is available.";
      printer.disabled = !data.printers.length;
      busy(false);
    } catch (error) {
      printer.innerHTML = "<option>Printer service unavailable</option>";
      status.textContent = error.message;
      busy(true);
    }
  };

  input.addEventListener("change", () => setFile(input.files[0]));
  remove.addEventListener("click", () => { input.value = ""; setFile(null); });
  for (const eventName of ["dragenter", "dragover"]) dropZone.addEventListener(eventName, event => { event.preventDefault(); dropZone.classList.add("dragging"); });
  for (const eventName of ["dragleave", "drop"]) dropZone.addEventListener(eventName, event => { event.preventDefault(); dropZone.classList.remove("dragging"); });
  dropZone.addEventListener("drop", event => setFile(event.dataTransfer.files[0]));

  printJobs.addEventListener("click", async () => {
    if (!window.confirm("Print all " + printJobs.dataset.count + " waiting PDF files?")) return;
    busy(true); status.textContent = "Sending PDFs to the printer…";
    try {
      const data = await request("/documents/api/print-jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ printer: printer.value }) });
      status.textContent = data.printed + " PDF " + (data.printed === 1 ? "was" : "were") + " sent to the printer.";
      await load();
    } catch (error) { status.textContent = error.message; busy(false); }
  });
  printFile.addEventListener("click", async () => {
    if (!selectedFile) return;
    busy(true); status.textContent = "Uploading and sending the PDF…";
    try {
      const url = "/documents/api/print-pdf?printer=" + encodeURIComponent(printer.value) + "&filename=" + encodeURIComponent(selectedFile.name);
      await request(url, { method: "POST", headers: { "Content-Type": "application/pdf" }, body: selectedFile });
      status.textContent = "The PDF was sent to the printer.";
      input.value = ""; setFile(null);
      await load();
    } catch (error) { status.textContent = error.message; busy(false); }
  });
  printer.addEventListener("change", () => busy(false));
  load();
})();
