(() => {
  "use strict";

  const t = window.appT || (message => message);
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const printer = document.getElementById("printer");
  const frame = document.getElementById("documentUploadFrame");
  const dropZone = document.getElementById("dropZone");
  const dropOverlay = document.getElementById("dropOverlay");
  const input = document.getElementById("fileInput");
  const queueView = document.getElementById("queueView");
  const queueSummary = document.getElementById("queueSummary");
  const fileQueue = document.getElementById("fileQueue");
  const addFiles = document.getElementById("addFiles");
  const progressView = document.getElementById("progressView");
  const progressFile = document.getElementById("progressFile");
  const progressCount = document.getElementById("progressCount");
  const resultView = document.getElementById("resultView");
  const resultVisual = document.getElementById("resultVisual");
  const resultIcon = document.getElementById("resultIcon");
  const resultTitle = document.getElementById("resultTitle");
  const resultText = document.getElementById("resultText");
  const resultList = document.getElementById("resultList");
  const resetQueue = document.getElementById("resetQueue");
  const printFile = document.getElementById("printFile");
  const status = document.getElementById("documentStatus");
  let files = [];
  let nextFileId = 1;
  let processing = false;
  let printerAvailable = false;
  let dragDepth = 0;

  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf };
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || t("The request could not be completed."));
    }
    return payload;
  };

  const formatSize = bytes => {
    if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  };

  const selectedMessage = count => count === 1
    ? t("1 PDF selected")
    : t("{count} PDFs selected", { count });

  const showView = view => {
    dropZone.hidden = view !== "drop";
    queueView.hidden = view !== "queue";
    progressView.hidden = view !== "progress";
    resultView.hidden = view !== "result";
  };

  const updateControls = () => {
    printer.disabled = processing || !printerAvailable;
    printFile.disabled = processing || !printerAvailable || files.length === 0;
    addFiles.classList.toggle("disabled", processing);
    addFiles.setAttribute("aria-disabled", String(processing));
    printFile.replaceChildren();
    const icon = document.createElement("i");
    icon.className = "fas fa-print button-icon";
    icon.setAttribute("aria-hidden", "true");
    printFile.append(icon, files.length > 1
      ? t("Print {count} PDFs", { count: files.length })
      : t("Print PDF"));
  };

  const makeFileRow = (entry, index, removable = false) => {
    const item = document.createElement("li");
    item.className = `document-queue-item state-${entry.state || "pending"}`;

    const position = document.createElement("span");
    position.className = "document-queue-position";
    position.textContent = String(index + 1);

    const icon = document.createElement("i");
    icon.className = entry.state === "sent"
      ? "far fa-check-circle document-queue-icon"
      : entry.state === "error"
        ? "far fa-times-circle document-queue-icon"
        : "far fa-file-pdf document-queue-icon";
    icon.setAttribute("aria-hidden", "true");

    const copy = document.createElement("div");
    copy.className = "document-queue-copy";
    const fileName = document.createElement("strong");
    fileName.textContent = entry.file.name;
    const detail = document.createElement("small");
    detail.textContent = entry.error || (entry.state === "sent" ? t("Sent") : formatSize(entry.file.size));
    copy.append(fileName, detail);
    item.append(position, icon, copy);

    if (removable) {
      const remove = document.createElement("button");
      remove.className = "icon-action document-remove-file";
      remove.type = "button";
      remove.dataset.fileId = String(entry.id);
      remove.setAttribute("aria-label", t("Remove {filename}", { filename: entry.file.name }));
      remove.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
      item.append(remove);
    }
    return item;
  };

  const renderQueue = () => {
    fileQueue.replaceChildren(...files.map((entry, index) => makeFileRow(entry, index, true)));
    queueSummary.textContent = selectedMessage(files.length);
    showView(files.length ? "queue" : "drop");
    status.textContent = files.length ? selectedMessage(files.length) : t("Ready.");
    updateControls();
  };

  const addSelectedFiles = fileList => {
    if (processing) return;
    const incoming = [...fileList];
    const pdfs = incoming.filter(file => file.name.toLowerCase().endsWith(".pdf"));
    const rejected = incoming.length - pdfs.length;
    files.push(...pdfs.map(file => ({ id: nextFileId++, file, state: "pending", error: "" })));
    input.value = "";
    renderQueue();
    if (rejected) {
      status.textContent = rejected === 1
        ? t("One non-PDF file was skipped.")
        : t("{count} non-PDF files were skipped.", { count: rejected });
    }
  };

  const loadPrinters = async () => {
    try {
      const data = await request("/documents/api/status");
      printer.replaceChildren();
      for (const item of data.printers) {
        const option = document.createElement("option");
        option.value = item.name;
        option.textContent = item.ready ? item.label : item.label + " — " + t("check printer");
        option.selected = item.name === data.defaultPrinter;
        printer.append(option);
      }
      printerAvailable = data.printers.length > 0;
      if (!printerAvailable) {
        const option = document.createElement("option");
        option.textContent = t("No document printer available");
        printer.append(option);
        status.textContent = t("No configured document printer is available.");
      } else {
        status.textContent = files.length ? selectedMessage(files.length) : t("Ready.");
      }
    } catch (error) {
      printer.replaceChildren();
      const option = document.createElement("option");
      option.textContent = t("Printer service unavailable");
      printer.append(option);
      printerAvailable = false;
      status.textContent = error.message;
    }
    updateControls();
  };

  const renderResult = completedFiles => {
    const sent = completedFiles.filter(entry => entry.state === "sent").length;
    const allSent = sent === completedFiles.length;
    resultVisual.className = `document-result-visual state-${allSent ? "done" : "error"}`;
    resultIcon.className = allSent ? "far fa-check-circle" : "far fa-frown-open";
    resultTitle.textContent = allSent ? t("All PDFs were sent") : t("Some PDFs need attention");
    resultText.textContent = allSent
      ? (sent === 1 ? t("The PDF was sent to the printer.") : t("{count} PDFs were sent to the printer.", { count: sent }))
      : t("{sent} of {total} PDFs were sent. Check the marked files below.", { sent, total: completedFiles.length });
    resultList.replaceChildren(...completedFiles.map((entry, index) => makeFileRow(entry, index)));
    status.textContent = resultText.textContent;
    showView("result");
  };

  input.addEventListener("change", () => addSelectedFiles(input.files));
  fileQueue.addEventListener("click", event => {
    const button = event.target.closest(".document-remove-file");
    if (!button || processing) return;
    files = files.filter(entry => entry.id !== Number(button.dataset.fileId));
    renderQueue();
  });

  const isFileDrag = event => [...(event.dataTransfer?.types || [])].includes("Files");
  frame.addEventListener("dragenter", event => {
    if (!isFileDrag(event) || processing) return;
    event.preventDefault();
    dragDepth += 1;
    frame.classList.add("dragging");
    dropOverlay.hidden = false;
  });
  frame.addEventListener("dragover", event => {
    if (!isFileDrag(event) || processing) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });
  frame.addEventListener("dragleave", event => {
    if (!isFileDrag(event) || processing) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) {
      frame.classList.remove("dragging");
      dropOverlay.hidden = true;
    }
  });
  frame.addEventListener("drop", event => {
    if (!isFileDrag(event) || processing) return;
    event.preventDefault();
    dragDepth = 0;
    frame.classList.remove("dragging");
    dropOverlay.hidden = true;
    addSelectedFiles(event.dataTransfer.files);
  });

  printFile.addEventListener("click", async () => {
    if (processing || !files.length || !printer.value) return;
    processing = true;
    const completedFiles = [...files];
    showView("progress");
    updateControls();

    for (let index = 0; index < completedFiles.length; index += 1) {
      const entry = completedFiles[index];
      progressFile.textContent = entry.file.name;
      progressCount.textContent = t("PDF {current} of {total}", { current: index + 1, total: completedFiles.length });
      status.textContent = t("Uploading and sending {filename}…", { filename: entry.file.name });
      try {
        const url = "/documents/api/print-pdf?printer=" + encodeURIComponent(printer.value) + "&filename=" + encodeURIComponent(entry.file.name);
        await request(url, { method: "POST", headers: { "Content-Type": "application/pdf" }, body: entry.file });
        entry.state = "sent";
      } catch (error) {
        entry.state = "error";
        entry.error = error.message;
      }
    }

    processing = false;
    files = [];
    updateControls();
    renderResult(completedFiles);
  });

  resetQueue.addEventListener("click", () => {
    files = [];
    input.value = "";
    renderQueue();
  });
  printer.addEventListener("change", updateControls);
  window.addEventListener("beforeunload", event => {
    if (!processing) return;
    event.preventDefault();
    event.returnValue = "";
  });

  renderQueue();
  loadPrinters();
})();
