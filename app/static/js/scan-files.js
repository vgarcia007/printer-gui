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
  const weekday = value => new Intl.DateTimeFormat("en", { weekday: "short" }).format(new Date(value));
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
    meta.textContent = `${formatSize(file.size)}${file.ocrFailed ? " · OCR needs attention" : ""}`;
    details.append(headline, meta);

    const actions = document.createElement("div");
    actions.className = "scan-file-actions";
    const download = document.createElement("a");
    download.className = "file-icon-button";
    download.href = "/scans/api/files/" + encodeURIComponent(file.filename) + "/download";
    download.setAttribute("aria-label", "Download " + file.filename);
    download.title = "Download";
    download.append(icon("fa-save"));
    const rename = iconButton("fa-keyboard", "Rename");
    const remove = iconButton("fa-trash-alt", "Delete");
    actions.append(download, rename, remove);
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
      input.setAttribute("aria-label", "New PDF name");
      const renameBottom = document.createElement("div");
      renameBottom.className = "rename-bottom";
      const prefixes = document.createElement("div");
      prefixes.className = "rename-prefixes";
      [["none", "No prefix"], ["date", "Date prefix"], ["datetime", "Date & time prefix"]].forEach(([value, label], index) => {
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
      cancel.textContent = "CANCEL";
      const save = document.createElement("button");
      save.type = "submit";
      save.className = "rename-save";
      save.textContent = "SAVE";
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
    messageFor(root).textContent = files.length ? `${files.length} saved ${files.length === 1 ? "PDF" : "PDFs"}` : "No scanned PDFs yet";
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "empty-files";
      empty.append(icon("fa-file-pdf"), document.createTextNode("Your next scan will appear here."));
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
  if (drawer) drawer.addEventListener("drawer:opened", loadAll);
  loadAll();
})();
