(() => {
  const root = document.getElementById("scanFiles");
  const message = document.getElementById("filesMessage");
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const request = async (url, options = {}) => {
    options.headers = { ...(options.headers || {}), "X-CSRFToken": csrf };
    if (options.body) options.headers["Content-Type"] = "application/json";
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || "The request could not be completed.");
    return data;
  };
  const formatSize = bytes => bytes < 1024 * 1024 ? Math.ceil(bytes / 1024) + " KB" : (bytes / 1024 / 1024).toFixed(1) + " MB";
  const makeButton = (label, className = "secondary") => {
    const node = document.createElement("button"); node.type = "button"; node.className = className; node.textContent = label; return node;
  };
  const load = async () => {
    root.replaceChildren(); message.textContent = "Loading files…";
    try {
      const data = await request("/scans/api/files");
      message.textContent = data.files.length ? data.files.length + " saved " + (data.files.length === 1 ? "scan" : "scans") : "No scans have been saved yet.";
      for (const file of data.files) {
        const article = document.createElement("article"); article.className = "scan-file";
        const head = document.createElement("div"); head.className = "scan-file-head";
        const info = document.createElement("div");
        const title = document.createElement("strong"); title.textContent = file.filename;
        const meta = document.createElement("div"); meta.className = "scan-file-meta";
        meta.textContent = new Date(file.modified).toLocaleString() + " · " + formatSize(file.size) + (file.ocrFailed ? " · OCR needs attention" : "");
        info.append(title, meta); head.append(info); article.append(head);
        const actions = document.createElement("div"); actions.className = "file-actions";
        const download = document.createElement("a"); download.className = "primary link-button"; download.textContent = "Download";
        download.href = "/scans/api/files/" + encodeURIComponent(file.filename) + "/download";
        const rename = makeButton("Rename"); const remove = makeButton("Delete", "secondary danger");
        actions.append(download, rename, remove); article.append(actions);
        const form = document.createElement("form"); form.className = "rename-form"; form.hidden = true;
        const input = document.createElement("input"); input.required = true; input.maxLength = 200;
        input.value = file.name.replace(/^\d{4}-\d{2}-\d{2}(?:-\d{2}-\d{2}-\d{2})?\s*/, "");
        const prefix = document.createElement("div"); prefix.className = "prefixes";
        [["date", "Date (recommended)"], ["datetime", "Date and time"], ["none", "No prefix"]].forEach(([value, label], index) => {
          const holder = document.createElement("label"); const radio = document.createElement("input");
          radio.type = "radio"; radio.name = "prefix-" + file.filename; radio.value = value; radio.checked = index === 0;
          holder.append(radio, " " + label); prefix.append(holder);
        });
        const save = document.createElement("button"); save.className = "primary"; save.textContent = "Save name";
        form.append(input, prefix, save); article.append(form);
        rename.addEventListener("click", () => { form.hidden = !form.hidden; if (!form.hidden) input.focus(); });
        remove.addEventListener("click", async () => {
          if (!window.confirm("Permanently delete “" + file.filename + "”?")) return;
          try { await request("/scans/api/files/" + encodeURIComponent(file.filename), { method: "DELETE" }); await load(); }
          catch (error) { message.textContent = error.message; }
        });
        form.addEventListener("submit", async event => {
          event.preventDefault(); const selected = form.querySelector("input[type=radio]:checked");
          try {
            await request("/scans/api/files/" + encodeURIComponent(file.filename), { method: "PUT", body: JSON.stringify({ name: input.value, prefix: selected.value }) });
            await load();
          } catch (error) { message.textContent = error.message; }
        });
        root.append(article);
      }
    } catch (error) { message.textContent = error.message; }
  };
  load();
})();
