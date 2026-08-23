(() => {
  const t = window.appT || (message => message);
  const locale = document.documentElement.lang === "de" ? "de-DE" : "en";
  const roots = [...document.querySelectorAll("[data-scan-file-list]")];
  if (!roots.length) return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf };
    if (options.body) options.headers["Content-Type"] = "application/json";
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || t("The request could not be completed."));
    return data;
  };
  const formatSize = bytes => bytes < 1024 * 1024
    ? Math.max(1, Math.ceil(bytes / 1024)) + " KB"
    : (bytes / 1024 / 1024).toFixed(1) + " MB";
  const weekday = value => new Intl.DateTimeFormat(locale, { weekday: "short" }).format(new Date(value));
  const icon = (name, style = "far") => {
    const node = document.createElement("i");
    node.className = `${style} ${name} fa-fw`;
    node.setAttribute("aria-hidden", "true");
    return node;
  };
  const iconButton = (name, label, style = "far") => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "file-icon-button";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.append(icon(name, style));
    return button;
  };
  const messageFor = root => document.getElementById(root.dataset.messageId);
  const printModalElement = document.getElementById("scanPrintModal");
  const printModal = printModalElement && window.bootstrap
    ? window.bootstrap.Modal.getOrCreateInstance(printModalElement)
    : null;
  const printFilename = document.getElementById("scanPrintFilename");
  const printerChoices = document.getElementById("scanPrinterChoices");
  const printStatus = document.getElementById("scanPrintStatus");
  const confirmPrint = document.getElementById("confirmScanPrint");
  let pendingPrintFile = null;

  const setConfirmLabel = (label, iconName = "fa-print") => {
    if (!confirmPrint) return;
    confirmPrint.replaceChildren(icon(iconName, "fas"), document.createTextNode(label));
  };
  const selectedPrinter = () => printerChoices?.querySelector('input[type="radio"]:checked')?.value || "";
  const openPrintDialog = async (root, file) => {
    if (!printModal || !printFilename || !printerChoices || !printStatus || !confirmPrint) {
      messageFor(root).textContent = t("The print dialog is unavailable.");
      return;
    }
    pendingPrintFile = file;
    printFilename.textContent = file.filename;
    printerChoices.replaceChildren();
    printStatus.textContent = t("Loading printers…");
    confirmPrint.disabled = true;
    setConfirmLabel(t("Print PDF"));
    printModal.show();
    try {
      const data = await request("/documents/api/status");
      const hasDefault = data.printers.some(item => item.name === data.defaultPrinter);
      data.printers.forEach((item, index) => {
        const choice = document.createElement("label");
        choice.className = "printer-choice";
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "scan-print-printer";
        radio.value = item.name;
        radio.checked = item.name === data.defaultPrinter || (!hasDefault && index === 0);
        const printerIcon = icon("fa-print", "fas");
        const copy = document.createElement("span");
        const printerName = document.createElement("strong");
        printerName.textContent = item.label || item.name;
        const printerState = document.createElement("small");
        printerState.textContent = item.ready ? t("Ready") : t("Check printer");
        copy.append(printerName, printerState);
        choice.append(radio, printerIcon, copy);
        const updateSelection = () => {
          printerChoices.querySelectorAll(".printer-choice").forEach(itemChoice => {
            const input = itemChoice.querySelector("input");
            itemChoice.classList.toggle("selected", Boolean(input?.checked));
          });
          confirmPrint.disabled = !selectedPrinter();
        };
        radio.addEventListener("change", updateSelection);
        printerChoices.append(choice);
        updateSelection();
      });
      if (!data.printers.length) {
        printStatus.textContent = t("No document printer is available.");
      } else {
        printStatus.textContent = t("Choose a printer, then confirm below.");
      }
    } catch (error) {
      printStatus.textContent = error.message;
    }
  };

  if (confirmPrint) {
    confirmPrint.addEventListener("click", async () => {
      const printer = selectedPrinter();
      if (!pendingPrintFile || !printer) return;
      confirmPrint.disabled = true;
      setConfirmLabel(t("Sending…"), "fa-spinner fa-spin");
      printStatus.textContent = t("Sending the PDF to the printer…");
      try {
        const data = await request(
          "/scans/api/files/" + encodeURIComponent(pendingPrintFile.filename) + "/print",
          { method: "POST", body: JSON.stringify({ printer }) },
        );
        printStatus.textContent = data.message;
        setConfirmLabel(t("Sent"), "fa-check");
      } catch (error) {
        printStatus.textContent = error.message;
        confirmPrint.disabled = false;
        setConfirmLabel(t("Try again"), "fa-print");
      }
    });
  }
  if (printModalElement) {
    printModalElement.addEventListener("hidden.bs.modal", () => { pendingPrintFile = null; });
  }

  const renderRow = (root, file) => {
    const row = document.createElement("article");
    row.className = "scan-file-row";
    const details = document.createElement("div");
    details.className = "scan-file-details";
    const headline = document.createElement("div");
    headline.className = "scan-file-headline";
    const name = document.createElement("strong");
    name.className = "scan-file-name";
    name.textContent = file.filename;
    const day = document.createElement("small");
    day.textContent = weekday(file.modified);
    headline.append(name, day);
    const meta = document.createElement("div");
    meta.className = "scan-file-meta";
    meta.textContent = `${formatSize(file.size)}${file.ocrFailed ? " · " + t("OCR needs attention") : ""}`;
    details.append(headline, meta);

    const actions = document.createElement("div");
    actions.className = "scan-file-actions";
    const print = iconButton("fa-print", t("Print"), "fas");
    const download = document.createElement("a");
    download.className = "file-icon-button";
    download.href = "/scans/api/files/" + encodeURIComponent(file.filename) + "/download";
    download.setAttribute("aria-label", t("Download {filename}", {filename: file.filename}));
    download.title = t("Download");
    download.append(icon("fa-save"));
    const rename = iconButton("fa-keyboard", t("Rename"));
    const remove = iconButton("fa-trash-alt", t("Delete"));
    actions.append(print, download, rename, remove);
    const bottom = document.createElement("div");
    bottom.className = "scan-file-bottom";
    bottom.append(meta, actions);
    details.append(bottom);
    row.append(details);

    const beginRename = () => {
      if (row.querySelector("form")) return;
      headline.hidden = true;
      bottom.hidden = true;
      const form = document.createElement("form");
      form.className = "rename-panel";
      const input = document.createElement("input");
      input.className = "rename-input";
      input.required = true;
      input.maxLength = 200;
      input.value = file.name.replace(/^\d{4}-\d{2}-\d{2}(?:-\d{2}-\d{2}-\d{2})?\s*/, "");
      input.setAttribute("aria-label", t("New PDF name"));
      const renameBottom = document.createElement("div");
      renameBottom.className = "rename-bottom";
      const prefixes = document.createElement("div");
      prefixes.className = "rename-prefixes";
      [["none", t("No prefix")], ["date", t("Date prefix")], ["datetime", t("Date & time prefix")]].forEach(([value, label], index) => {
        const holder = document.createElement("label");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "prefix-" + file.filename;
        radio.value = value;
        radio.checked = index === 1;
        holder.append(radio, document.createTextNode(label));
        prefixes.append(holder);
      });
      const renameActions = document.createElement("div");
      renameActions.className = "rename-actions";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "rename-cancel";
      cancel.textContent = t("CANCEL");
      const save = document.createElement("button");
      save.type = "submit";
      save.className = "rename-save";
      save.textContent = t("SAVE");
      renameActions.append(cancel, save);
      renameBottom.append(prefixes, renameActions);
      form.append(input, renameBottom);
      row.prepend(form);
      input.focus();
      input.select();
      const close = () => {
        form.remove();
        headline.hidden = false;
        bottom.hidden = false;
      };
      cancel.addEventListener("click", close);
      input.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
      form.addEventListener("submit", async event => {
        event.preventDefault();
        save.disabled = true;
        const selected = form.querySelector('input[type="radio"]:checked');
        try {
          await request("/scans/api/files/" + encodeURIComponent(file.filename), {
            method: "PUT",
            body: JSON.stringify({ name: input.value, prefix: selected.value }),
          });
          await loadAll();
        } catch (error) {
          messageFor(root).textContent = error.message;
          save.disabled = false;
          input.focus();
        }
      });
    };
    print.addEventListener("click", () => openPrintDialog(root, file));
    rename.addEventListener("click", beginRename);
    remove.addEventListener("click", async () => {
      if (!window.confirm(t("Permanently delete “{filename}”?", {filename: file.filename}))) return;
      try {
        await request("/scans/api/files/" + encodeURIComponent(file.filename), { method: "DELETE" });
        await loadAll();
      } catch (error) { messageFor(root).textContent = error.message; }
    });
    return row;
  };

  const render = (root, files) => {
    root.replaceChildren();
    messageFor(root).textContent = files.length
      ? t(files.length === 1 ? "{count} saved PDF" : "{count} saved PDFs", {count: files.length})
      : t("No scanned PDFs yet");
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "empty-files";
      empty.append(icon("fa-file-pdf"), document.createTextNode(t("Your next scan will appear here.")));
      root.append(empty);
      return;
    }
    files.forEach(file => root.append(renderRow(root, file)));
  };
  const loadAll = async () => {
    roots.forEach(root => { messageFor(root).textContent = t("Loading files…"); });
    try {
      const data = await request("/scans/api/files");
      roots.forEach(root => render(root, data.files));
    } catch (error) {
      roots.forEach(root => { messageFor(root).textContent = error.message; });
    }
  };
  window.ScanFiles = { refresh: loadAll };
  const drawer = document.getElementById("scanFilesDrawer");
  if (drawer) drawer.addEventListener("drawer:opened", loadAll);
  loadAll();
})();
