(() => {
  const form = document.getElementById("labelEditorForm");
  const editor = document.getElementById("labelEditor");
  const submitButton = document.getElementById("editorSubmit");
  const saveButton = document.getElementById("editorSave");
  const errorBox = document.getElementById("editorError");
  const fontFamily = document.getElementById("fontFamily");
  const fontSize = document.getElementById("fontSize");
  const clearButton = document.getElementById("clearEditor");
  const insertImageButton = document.getElementById("insertImage");
  const imageFile = document.getElementById("imageFile");
  const imageTools = document.getElementById("imageTools");
  const imageSizeButtons = document.querySelectorAll("[data-image-size-choice]");
  const imageDelete = document.getElementById("imageDelete");
  const editorStatus = document.getElementById("editorStatus");
  if (!form || !editor || !submitButton || !saveButton) return;

  const storageKey = `dymo-label-editor-v2-${form.dataset.editorId || "new"}`;
  let savedRange = null;
  let submitting = false;
  let selectedImage = null;

  const selectionInsideEditor = () => {
    const selection = window.getSelection();
    return Boolean(
      selection &&
      selection.rangeCount &&
      editor.contains(selection.anchorNode)
    );
  };

  const rememberSelection = () => {
    if (selectionInsideEditor()) {
      savedRange = window.getSelection().getRangeAt(0).cloneRange();
    }
  };

  const restoreSelection = () => {
    editor.focus({ preventScroll: true });
    if (!savedRange || !editor.contains(savedRange.commonAncestorContainer)) return;
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(savedRange);
  };

  const showError = message => {
    errorBox.textContent = message;
    errorBox.hidden = false;
    errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const hideError = () => {
    errorBox.hidden = true;
  };

  const labelText = () => editor.innerText.replace(/\u00a0/g, " ").trim();
  const hasImage = () => Boolean(editor.querySelector(".editor-image"));
  const hasContent = () => Boolean(labelText() || hasImage());

  const normalizeFormatting = root => {
    root.querySelectorAll("[style]").forEach(node => {
      if (["DIV", "P"].includes(node.tagName)) {
        const alignment = (node.style.textAlign || "").toLowerCase();
        if (["left", "center", "right"].includes(alignment)) {
          node.setAttribute("align", alignment);
        }
      }
      node.removeAttribute("style");
    });
    return root;
  };

  const normalizedDocument = content => {
    const parsed = new DOMParser().parseFromString(content, "text/html");
    return normalizeFormatting(parsed.body).innerHTML;
  };

  const updateResponsiveFontSizes = () => {
    const width = editor.clientWidth;
    if (!width) return;
    editor.style.setProperty("--label-font-small", `${width * 0.03}px`);
    editor.style.setProperty("--label-font-medium", `${width * 0.04}px`);
    editor.style.setProperty("--label-font-large", `${width * 0.052}px`);
    editor.style.setProperty("--label-font-extra-large", `${width * 0.065}px`);
    editor.style.setProperty("--label-font-largest", `${width * 0.08}px`);
  };

  const updateEditorStatus = saved => {
    const count = labelText().length;
    const state = saved && hasContent() ? "Draft saved" : "Ready";
    editorStatus.textContent = `${state} · ${count.toLocaleString("en-US")} / 2,000 characters`;
  };

  const serializedDocument = () => {
    const documentClone = editor.cloneNode(true);
    documentClone.querySelectorAll(".is-selected").forEach(node =>
      node.classList.remove("is-selected")
    );
    return normalizeFormatting(documentClone).innerHTML;
  };

  const selectImage = wrapper => {
    if (selectedImage) selectedImage.classList.remove("is-selected");
    selectedImage = wrapper;
    if (selectedImage) selectedImage.classList.add("is-selected");
    imageTools.hidden = !selectedImage;
    imageSizeButtons.forEach(button => {
      const active = Boolean(
        selectedImage &&
        button.dataset.imageSizeChoice === selectedImage.dataset.imageSize
      );
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  };

  const updateOverflowState = () => {
    const overflows =
      editor.scrollHeight > editor.clientHeight + 2 ||
      editor.scrollWidth > editor.clientWidth + 2;
    editor.classList.toggle("is-overflowing", overflows);
    editor.setAttribute("aria-invalid", overflows ? "true" : "false");
    return overflows;
  };

  const saveDraft = () => {
    try {
      if (hasContent()) {
        localStorage.setItem(storageKey, serializedDocument());
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch (_error) {
      // The editor remains fully usable when private browsing blocks storage.
    }
    updateEditorStatus(true);
  };

  try {
    document.execCommand("styleWithCSS", false, false);
    const draft = localStorage.getItem(storageKey);
    const initialDocumentNode = document.getElementById("initialEditorDocument");
    const initialDocument = initialDocumentNode
      ? JSON.parse(initialDocumentNode.textContent)
      : "";
    const content = form.dataset.editorMode === "copy"
      ? initialDocument
      : draft || initialDocument;
    if (content) {
      editor.innerHTML = normalizedDocument(content);
      editor.querySelectorAll(".is-selected").forEach(node => node.classList.remove("is-selected"));
      editor.querySelectorAll(".editor-image").forEach(image => {
        image.addEventListener("load", updateOverflowState, { once: true });
      });
    }
  } catch (_error) {
    // Ignore unavailable storage.
  }

  document.addEventListener("selectionchange", () => {
    rememberSelection();
    document.querySelectorAll("[data-command]").forEach(button => {
      const command = button.dataset.command;
      if (!["bold", "italic", "underline", "justifyLeft", "justifyCenter", "justifyRight"].includes(command)) return;
      try {
        const active = document.queryCommandState(command);
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      } catch (_error) {
        button.classList.remove("is-active");
        button.setAttribute("aria-pressed", "false");
      }
    });
  });

  editor.addEventListener("input", () => {
    hideError();
    updateOverflowState();
    saveDraft();
  });

  const imageFromFile = async file => {
    if (file.size > 20 * 1024 * 1024) {
      throw new Error("The selected image is too large.");
    }
    const objectUrl = URL.createObjectURL(file);
    const source = new Image();
    try {
      await new Promise((resolve, reject) => {
        source.onload = resolve;
        source.onerror = () => reject(new Error("The selected image could not be read."));
        source.src = objectUrl;
      });

      if (source.naturalWidth * source.naturalHeight > 40_000_000) {
        throw new Error("The clipboard image contains too many pixels.");
      }

      const maxEdge = 1400;
      const scale = Math.min(1, maxEdge / Math.max(source.naturalWidth, source.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(source.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(source.naturalHeight * scale));
      const context = canvas.getContext("2d");
      context.fillStyle = "#fff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(source, 0, 0, canvas.width, canvas.height);
      const png = canvas.toDataURL("image/png");
      return png.length <= 1_500_000
        ? png
        : canvas.toDataURL("image/jpeg", 0.9);
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  };

  const insertImage = source => {
    const wrapper = document.createElement("span");
    wrapper.className = "editor-image-wrap";
    wrapper.dataset.imageSize = "medium";
    wrapper.contentEditable = "false";

    const image = document.createElement("img");
    image.className = "editor-image";
    image.src = source;
    image.alt = "Pasted image";
    image.draggable = false;
    image.addEventListener("load", updateOverflowState, { once: true });
    wrapper.append(image);

    let range = savedRange;
    if (!range || !editor.contains(range.commonAncestorContainer)) {
      range = document.createRange();
      range.selectNodeContents(editor);
      range.collapse(false);
    }
    range.deleteContents();
    range.insertNode(wrapper);
    const spacer = document.createTextNode("\u00a0");
    wrapper.after(spacer);
    range.setStartAfter(spacer);
    range.collapse(true);
    savedRange = range.cloneRange();
    selectImage(wrapper);
    hideError();
    saveDraft();
    updateOverflowState();
  };

  editor.addEventListener("paste", async event => {
    const imageItem = Array.from(event.clipboardData.items || []).find(item =>
      item.type.startsWith("image/")
    );
    if (imageItem) {
      event.preventDefault();
      rememberSelection();
      try {
        const file = imageItem.getAsFile();
        if (!file) throw new Error("No readable image was found on the clipboard.");
        insertImage(await imageFromFile(file));
      } catch (error) {
        showError(error.message || "The image could not be pasted.");
      }
      return;
    }

    event.preventDefault();
    const text = event.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  });

  editor.addEventListener("click", event => {
    const wrapper = event.target.closest(".editor-image-wrap");
    selectImage(wrapper && editor.contains(wrapper) ? wrapper : null);
  });

  insertImageButton.addEventListener("click", () => imageFile.click());
  imageFile.addEventListener("change", async () => {
    const file = imageFile.files && imageFile.files[0];
    if (!file) return;
    try {
      insertImage(await imageFromFile(file));
    } catch (error) {
      showError(error.message || "The image could not be inserted.");
    } finally {
      imageFile.value = "";
    }
  });

  document.querySelectorAll("[data-command]").forEach(button => {
    button.addEventListener("pointerdown", event => event.preventDefault());
    button.addEventListener("click", () => {
      restoreSelection();
      document.execCommand(button.dataset.command, false);
      rememberSelection();
      saveDraft();
      updateOverflowState();
    });
  });

  fontFamily.addEventListener("pointerdown", rememberSelection);
  fontFamily.addEventListener("change", () => {
    restoreSelection();
    document.execCommand("fontName", false, fontFamily.value);
    rememberSelection();
    saveDraft();
    updateOverflowState();
  });

  fontSize.addEventListener("pointerdown", rememberSelection);
  fontSize.addEventListener("change", () => {
    restoreSelection();
    document.execCommand("fontSize", false, fontSize.value);
    rememberSelection();
    saveDraft();
    updateOverflowState();
  });

  clearButton.addEventListener("click", () => {
    if (hasContent() && !window.confirm("Clear the current label?")) return;
    editor.replaceChildren();
    savedRange = null;
    selectImage(null);
    saveDraft();
    updateOverflowState();
    hideError();
    editor.focus();
  });

  const setSelectedImageSize = size => {
    if (!selectedImage) return;
    selectedImage.dataset.imageSize = size;
    selectImage(selectedImage);
    saveDraft();
    updateOverflowState();
  };

  imageSizeButtons.forEach(button => {
    button.addEventListener("click", () => {
      setSelectedImageSize(button.dataset.imageSizeChoice);
    });
  });
  imageDelete.addEventListener("click", () => {
    if (!selectedImage) return;
    const wrapper = selectedImage;
    selectImage(null);
    wrapper.remove();
    if (!hasContent()) editor.replaceChildren();
    saveDraft();
    updateOverflowState();
    editor.focus();
  });

  const renderToCanvas = async () => {
    if (typeof window.html2canvas !== "function") {
      throw new Error("The print renderer did not load. Reload the page and try again.");
    }
    const width = Number(form.dataset.outputWidth);
    const height = Number(form.dataset.outputHeight);
    const editorRect = editor.getBoundingClientRect();
    const renderedEditor = await window.html2canvas(editor, {
      backgroundColor: "#ffffff",
      logging: false,
      scale: Math.max(width / editorRect.width, height / editorRect.height),
      useCORS: false,
      onclone: clonedDocument => {
        const clonedEditor = clonedDocument.getElementById("labelEditor");
        clonedEditor.removeAttribute("contenteditable");
        clonedEditor.querySelectorAll(".is-selected").forEach(node => {
          node.classList.remove("is-selected");
        });
      },
    });

    const output = document.createElement("canvas");
    output.width = width;
    output.height = height;
    const context = output.getContext("2d");
    context.fillStyle = "#fff";
    context.fillRect(0, 0, width, height);
    context.drawImage(renderedEditor, 0, 0, width, height);
    return output;
  };

  const waitForImages = () => Promise.all(
    Array.from(editor.querySelectorAll(".editor-image")).map(image => {
      if (image.complete && image.naturalWidth) return Promise.resolve();
      return new Promise((resolve, reject) => {
        image.addEventListener("load", resolve, { once: true });
        image.addEventListener("error", () => reject(new Error("A pasted image could not be loaded.")), { once: true });
      });
    })
  );

  const canvasBlob = canvas => new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(new Error("The print preview could not be created."));
    }, "image/png");
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (submitting) return;
    hideError();

    const text = labelText();
    const editorAction = (
      event.submitter && event.submitter.dataset.editorAction
    ) || "preview";
    const activeButton = editorAction === "save" ? saveButton : submitButton;
    if (!text && !hasImage()) {
      showError("Enter text or paste an image from the clipboard.");
      editor.focus();
      return;
    }
    if (text.length > 2000) {
      showError("The text is too long.");
      return;
    }
    if (updateOverflowState()) {
      showError("The content extends beyond the printable area. Make it smaller.");
      return;
    }

    submitting = true;
    submitButton.disabled = true;
    saveButton.disabled = true;
    submitButton.classList.add("is-loading");
    if (activeButton === saveButton) {
      saveButton.textContent = "Saving…";
    } else {
      submitButton.firstChild.textContent = "Creating preview… ";
    }

    try {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await waitForImages();
      const blob = await canvasBlob(await renderToCanvas());
      const formData = new FormData(form);
      formData.set("editor_text", text);
      formData.set("editor_content", serializedDocument());
      formData.set("editor_action", editorAction);
      formData.set("png_file", blob, "label.png");
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: { "X-Requested-With": "fetch" },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || "The label could not be created.");
      }
      localStorage.removeItem(storageKey);
      window.location.assign(payload.redirect_url);
    } catch (error) {
      submitting = false;
      submitButton.disabled = false;
      saveButton.disabled = false;
      submitButton.classList.remove("is-loading");
      submitButton.firstChild.textContent = "Continue to print →";
      saveButton.textContent = "Save";
      showError(error.message || "The label could not be created.");
    }
  });

  updateOverflowState();
  updateEditorStatus(false);
  updateResponsiveFontSizes();
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => {
      updateResponsiveFontSizes();
      updateOverflowState();
    }).observe(editor);
  } else {
    window.addEventListener("resize", updateResponsiveFontSizes);
  }
})();
