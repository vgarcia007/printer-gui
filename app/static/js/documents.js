(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const printer = document.getElementById("printer");
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
