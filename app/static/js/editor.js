(() => {
  const form = document.getElementById("labelEditorForm");
  const editor = document.getElementById("labelEditor");
  const labelViewport = document.getElementById("labelViewport");
  const labelStage = document.getElementById("labelStage");
  const submitButton = document.getElementById("editorSubmit");
  const saveButton = document.getElementById("editorSave");
  const saveButtonLabel = saveButton.querySelector(".button-label");
  const submitButtonLabel = submitButton.querySelector(".button-label");
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

  const outputWidth = Number(form.dataset.outputWidth);
  const outputHeight = Number(form.dataset.outputHeight);
  const printDpi = 300;
  const cssDpi = 96;
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

  const updateViewportScale = () => {
    const stageStyle = getComputedStyle(labelStage);
    const intrinsicWidth = parseFloat(stageStyle.width);
    const intrinsicHeight = parseFloat(stageStyle.height);
    const scale = labelViewport.clientWidth / intrinsicWidth;
    labelStage.style.transform = `scale(${scale})`;
    labelViewport.style.height = `${intrinsicHeight * scale}px`;
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

  const coordinate = value => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const setImagePosition = (wrapper, xPercent, yPercent) => {
    const widthPercent = editor.clientWidth
      ? wrapper.offsetWidth / editor.clientWidth * 100
      : 0;
    const heightPercent = editor.clientHeight
      ? wrapper.offsetHeight / editor.clientHeight * 100
      : 0;
    const x = Math.max(0, Math.min(100 - widthPercent, xPercent));
    const y = Math.max(0, Math.min(100 - heightPercent, yPercent));
    wrapper.dataset.imageX = x.toFixed(3).replace(/\.?0+$/, "");
    wrapper.dataset.imageY = y.toFixed(3).replace(/\.?0+$/, "");
    wrapper.style.left = `${x}%`;
    wrapper.style.top = `${y}%`;
  };

  const applyImagePosition = wrapper => {
    setImagePosition(
      wrapper,
      coordinate(wrapper.dataset.imageX || "2.273"),
      coordinate(wrapper.dataset.imageY || "5.882")
    );
  };

  const prepareImageWrapper = wrapper => {
    if (!wrapper.dataset.imageSize) wrapper.dataset.imageSize = "medium";
    if (!wrapper.dataset.imageX) wrapper.dataset.imageX = "2.273";
    if (!wrapper.dataset.imageY) wrapper.dataset.imageY = "5.882";
    wrapper.contentEditable = "false";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("aria-label", "Positioned image. Drag it or use the arrow keys to move it.");
    applyImagePosition(wrapper);
    if (wrapper._positioningReady) return;
    wrapper._positioningReady = true;

    wrapper.addEventListener("pointerdown", event => {
      if (event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      selectImage(wrapper);
      wrapper.focus({ preventScroll: true });
      const editorRect = editor.getBoundingClientRect();
      const scaleX = editor.clientWidth / editorRect.width;
      const scaleY = editor.clientHeight / editorRect.height;
      const startX = event.clientX;
      const startY = event.clientY;
      const startLeft = wrapper.offsetLeft;
      const startTop = wrapper.offsetTop;
      wrapper.setPointerCapture(event.pointerId);

      const move = moveEvent => {
        const left = startLeft + (moveEvent.clientX - startX) * scaleX;
        const top = startTop + (moveEvent.clientY - startY) * scaleY;
        setImagePosition(
          wrapper,
          left / editor.clientWidth * 100,
          top / editor.clientHeight * 100
        );
      };
      const finish = () => {
        wrapper.removeEventListener("pointermove", move);
        wrapper.removeEventListener("pointerup", finish);
        wrapper.removeEventListener("pointercancel", finish);
        saveDraft();
        updateOverflowState();
      };
      wrapper.addEventListener("pointermove", move);
      wrapper.addEventListener("pointerup", finish);
      wrapper.addEventListener("pointercancel", finish);
    });

    wrapper.addEventListener("keydown", event => {
      const directions = {
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
        ArrowUp: [0, -1],
        ArrowDown: [0, 1],
      };
      if (!directions[event.key]) return;
      event.preventDefault();
      const stepMm = event.shiftKey ? 2 : 0.5;
      const stepPx = stepMm * cssDpi / 25.4;
      const [horizontal, vertical] = directions[event.key];
      setImagePosition(
        wrapper,
        (wrapper.offsetLeft + horizontal * stepPx) / editor.clientWidth * 100,
        (wrapper.offsetTop + vertical * stepPx) / editor.clientHeight * 100
      );
      saveDraft();
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
      editor.querySelectorAll(".editor-image-wrap").forEach(prepareImageWrapper);
      editor.querySelectorAll(".editor-image").forEach(image => {
        image.addEventListener("load", () => {
          applyImagePosition(image.closest(".editor-image-wrap"));
          updateOverflowState();
        }, { once: true });
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
    wrapper.dataset.imageX = "2.273";
    wrapper.dataset.imageY = "5.882";
    wrapper.contentEditable = "false";

    const image = document.createElement("img");
    image.className = "editor-image";
    image.src = source;
    image.alt = "Pasted image";
    image.draggable = false;
    image.addEventListener("load", () => {
      applyImagePosition(wrapper);
      updateOverflowState();
    }, { once: true });
    wrapper.append(image);
    prepareImageWrapper(wrapper);
    editor.append(wrapper);
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
    requestAnimationFrame(() => {
      applyImagePosition(selectedImage);
      saveDraft();
      updateOverflowState();
    });
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
    const editorStyle = getComputedStyle(editor);
    const cssWidth = parseFloat(editorStyle.width);
    const cssHeight = parseFloat(editorStyle.height);
    const renderedEditor = await window.html2canvas(editor, {
      backgroundColor: "#ffffff",
      logging: false,
      scale: printDpi / cssDpi,
      width: cssWidth,
      height: cssHeight,
      useCORS: false,
      onclone: clonedDocument => {
        const clonedViewport = clonedDocument.getElementById("labelViewport");
        const clonedStage = clonedDocument.getElementById("labelStage");
        const clonedEditor = clonedDocument.getElementById("labelEditor");
        clonedViewport.style.width = `${cssWidth}px`;
        clonedViewport.style.height = `${cssHeight}px`;
        clonedViewport.style.overflow = "visible";
        clonedStage.style.transform = "none";
        clonedEditor.removeAttribute("contenteditable");
        clonedEditor.querySelectorAll(".is-selected").forEach(node => {
          node.classList.remove("is-selected");
        });
      },
    });
    if (Math.abs(renderedEditor.width - outputWidth) > 1 || Math.abs(renderedEditor.height - outputHeight) > 1) {
      throw new Error("The browser did not create an exact-size print image.");
    }
    const output = document.createElement("canvas");
    output.width = outputWidth;
    output.height = outputHeight;
    const context = output.getContext("2d");
    context.fillStyle = "#fff";
    context.fillRect(0, 0, outputWidth, outputHeight);
    context.drawImage(renderedEditor, 0, 0);
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
      saveButtonLabel.textContent = "Saving…";
    } else {
      submitButtonLabel.textContent = "Creating preview…";
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
      submitButtonLabel.textContent = "Continue to print";
      saveButtonLabel.textContent = "Save";
      showError(error.message || "The label could not be created.");
    }
  });

  updateOverflowState();
  updateEditorStatus(false);
  updateViewportScale();
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => {
      updateViewportScale();
      updateOverflowState();
    }).observe(labelViewport);
  } else {
    window.addEventListener("resize", updateViewportScale);
  }
})();
