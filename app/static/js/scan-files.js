(() => {
  const roots = [...document.querySelectorAll("[data-scan-file-list]")];
  if (!roots.length) return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf };
    if (options.body) options.headers["Content-Type"] = "application/json";
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || "The request could not be completed.");
    return data;
  };
  const formatSize = bytes => bytes < 1024 * 1024
    ? Math.max(1, Math.ceil(bytes / 1024)) + " KB"
    : (bytes / 1024 / 1024).toFixed(1) + " MB";
  const formatDate = value => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  const icon = name => {
    const node = document.createElement("i");
    node.className = `fa-solid ${name}`;
    node.setAttribute("aria-hidden", "true");
    return node;
  };
  const iconButton = (name, label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "icon-action";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.append(icon(name));
    return button;
  };
  const messageFor = root => document.getElementById(root.dataset.messageId);

  const renderRow = (root, file) => {
    const row = document.createElement("article");
    row.className = "scan-file-row";
    const symbol = document.createElement("span");
    symbol.className = "pdf-symbol";
    symbol.append(icon("fa-file-pdf"));
    const details = document.createElement("div");
    details.className = "scan-file-details";
    const name = document.createElement("button");
    name.type = "button";
    name.className = "scan-file-name";
    name.textContent = file.name;
    name.title = "Rename";
    const meta = document.createElement("small");
    meta.textContent = `${formatDate(file.modified)} · ${formatSize(file.size)}${file.ocrFailed ? " · OCR needs attention" : ""}`;
    details.append(name, meta);
    const actions = document.createElement("div");
    actions.className = "scan-file-actions";
    const download = document.createElement("a");
    download.className = "icon-action";
    download.href = "/scans/api/files/" + encodeURIComponent(file.filename) + "/download";
    download.setAttribute("aria-label", "Download " + file.filename);
    download.title = "Download";
    download.append(icon("fa-download"));
    const rename = iconButton("fa-pen", "Rename");
    const remove = iconButton("fa-trash-can", "Delete");
    remove.classList.add("danger-action");
    actions.append(download, rename, remove);
    row.append(symbol, details, actions);

    const beginRename = () => {
      if (details.querySelector("form")) return;
      name.hidden = true;
      meta.hidden = true;
      const form = document.createElement("form");
      form.className = "inline-rename";
      const input = document.createElement("input");
      input.required = true;
      input.maxLength = 200;
      input.value = file.name;
      input.setAttribute("aria-label", "New PDF name");
      const save = iconButton("fa-check", "Save name");
      save.type = "submit";
      const cancel = iconButton("fa-xmark", "Cancel rename");
      form.append(input, save, cancel);
      details.prepend(form);
      input.focus();
      input.select();
      const close = () => { form.remove(); name.hidden = false; meta.hidden = false; };
      cancel.addEventListener("click", close);
      input.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
      form.addEventListener("submit", async event => {
        event.preventDefault();
        save.disabled = true;
        try {
          await request("/scans/api/files/" + encodeURIComponent(file.filename), {
            method: "PUT",
            body: JSON.stringify({ name: input.value, prefix: "none" }),
          });
          await loadAll();
        } catch (error) {
          messageFor(root).textContent = error.message;
          save.disabled = false;
          input.focus();
        }
      });
    };
    name.addEventListener("click", beginRename);
    rename.addEventListener("click", beginRename);
    remove.addEventListener("click", async () => {
      if (!window.confirm("Permanently delete “" + file.filename + "”?")) return;
      try {
        await request("/scans/api/files/" + encodeURIComponent(file.filename), { method: "DELETE" });
        await loadAll();
      } catch (error) { messageFor(root).textContent = error.message; }
    });
    return row;
  };

  const render = (root, files) => {
    root.replaceChildren();
    const message = messageFor(root);
    message.textContent = files.length ? `${files.length} saved ${files.length === 1 ? "PDF" : "PDFs"}` : "No scanned PDFs yet";
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "empty-files";
      empty.append(icon("fa-file-circle-plus"), "Your next scan will appear here.");
      root.append(empty);
      return;
    }
    files.forEach(file => root.append(renderRow(root, file)));
  };
  const loadAll = async () => {
    roots.forEach(root => { messageFor(root).textContent = "Loading files…"; });
    try {
      const data = await request("/scans/api/files");
      roots.forEach(root => render(root, data.files));
    } catch (error) {
      roots.forEach(root => { messageFor(root).textContent = error.message; });
    }
  };
  window.ScanFiles = { refresh: loadAll };

  const drawer = document.getElementById("scanFilesDrawer");
  const open = document.getElementById("openScanFiles");
  const close = document.getElementById("closeScanFiles");
  const scrim = document.getElementById("scanFilesScrim");
  if (drawer && open && close && scrim) {
    let hideScrimTimer = null;
    const setOpen = value => {
      drawer.classList.toggle("open", value);
      drawer.setAttribute("aria-hidden", String(!value));
      open.setAttribute("aria-expanded", String(value));
      document.body.classList.toggle("drawer-open", value);
      if (value) {
        window.clearTimeout(hideScrimTimer);
        scrim.hidden = false;
        requestAnimationFrame(() => scrim.classList.add("open"));
        close.focus({ preventScroll: true });
        loadAll();
      } else {
        scrim.classList.remove("open");
        hideScrimTimer = window.setTimeout(() => { scrim.hidden = true; }, 180);
        open.focus({ preventScroll: true });
      }
    };
    open.addEventListener("click", () => setOpen(true));
    close.addEventListener("click", () => setOpen(false));
    scrim.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", event => { if (event.key === "Escape" && drawer.classList.contains("open")) setOpen(false); });
  }
  loadAll();
})();
