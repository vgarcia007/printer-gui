(() => {
  const t = window.appT || (message => message);
  const locale = document.documentElement.lang === "de" ? "de-DE" : "en-US";
  const form = document.getElementById("labelEditorForm");
  const editor = document.getElementById("labelEditor");
  const labelViewport = document.getElementById("labelViewport");
  const labelStage = document.getElementById("labelStage");
  const submitButton = document.getElementById("editorSubmit");
  const saveButton = document.getElementById("editorSave");
  const saveButtonLabel = saveButton.querySelector(".button-label");
  const submitButtonLabel = submitButton.querySelector(".button-label");
  const errorBox = document.getElementById("editorError");
  const fontPicker = document.getElementById("fontPicker");
  const fontPickerButton = document.getElementById("fontPickerButton");
  const fontPickerLabel = document.getElementById("fontPickerLabel");
  const fontPickerMenu = document.getElementById("fontPickerMenu");
  const fontPickerOptions = document.querySelectorAll("[data-font-family]");
  const fontSize = document.getElementById("fontSize");
  const clearButton = document.getElementById("clearEditor");
  const insertTextButton = document.getElementById("insertText");
  const insertImageButton = document.getElementById("insertImage");
  const imageFile = document.getElementById("imageFile");
  const insertSymbolButton = document.getElementById("insertSymbol");
  const symbolPalette = document.getElementById("symbolPalette");
  const closeSymbolPaletteButton = document.getElementById("closeSymbolPalette");
  const symbolChoices = document.querySelectorAll("[data-symbol-glyph]");
  const deleteSelectedButton = document.getElementById("deleteSelected");
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
  let selectedText = null;
  const imageSizeLimits = {
    small: { width: 24, height: 36 },
    medium: { width: 42, height: 56 },
    large: { width: 62, height: 72 },
    full: { width: 84, height: 88 },
  };

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
    const textBox = selectedText && selectedText.querySelector(".editor-text-box");
    if (textBox) textBox.focus({ preventScroll: true });
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

  const labelText = () => Array.from(editor.querySelectorAll(".editor-text-box"))
    .map(textBox => textBox.innerText.replace(/\u00a0/g, " ").trim())
    .filter(Boolean)
    .join("\n");
  const hasImage = () => Boolean(editor.querySelector(".editor-image"));
  const hasContent = () => Boolean(labelText() || hasImage());

  const updateEmptyState = () => {
    editor.classList.toggle("is-empty", !hasContent());
  };

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
    const state = saved && hasContent() ? t("Draft saved") : t("Ready");
    editorStatus.textContent = `${state} · ${count.toLocaleString(locale)} / ${Number(2000).toLocaleString(locale)} ${t("characters")}`;
  };

  const serializedDocument = () => {
    const documentClone = editor.cloneNode(true);
    documentClone.querySelectorAll(".image-resize-handle,.text-box-control").forEach(node => node.remove());
    documentClone.querySelectorAll(".editor-text-wrap").forEach(wrapper => {
      const textBox = wrapper.querySelector(".editor-text-box");
      if (!textBox || !textBox.textContent.replace(/\u00a0/g, " ").trim()) wrapper.remove();
    });
    documentClone.querySelectorAll(".is-selected").forEach(node =>
      node.classList.remove("is-selected")
    );
    return normalizeFormatting(documentClone).innerHTML;
  };

  const selectImage = wrapper => {
    if (selectedImage) selectedImage.classList.remove("is-selected");
    if (selectedText) selectedText.classList.remove("is-selected");
    selectedText = null;
    selectedImage = wrapper;
    if (selectedImage) selectedImage.classList.add("is-selected");
    deleteSelectedButton.disabled = !selectedImage;
  };

  const selectText = wrapper => {
    if (selectedImage) selectedImage.classList.remove("is-selected");
    selectedImage = null;
    if (selectedText) selectedText.classList.remove("is-selected");
    selectedText = wrapper;
    if (selectedText) selectedText.classList.add("is-selected");
    deleteSelectedButton.disabled = !selectedText;
  };

  const coordinate = value => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const compactCoordinate = value =>
    value.toFixed(3).replace(/\.?0+$/, "") || "0";

  const fitImageToLabel = wrapper => {
    const image = wrapper.querySelector(".editor-image");
    if (!image || !image.naturalWidth || !image.naturalHeight || !editor.clientWidth || !editor.clientHeight) {
      return false;
    }
    const limits = imageSizeLimits[wrapper.dataset.imageSize] || imageSizeLimits.medium;
    const requestedWidth = coordinate(wrapper.dataset.imageWidth);
    const customWidth = requestedWidth > 0;
    const maximumWidth = editor.clientWidth * Math.min(customWidth ? requestedWidth : limits.width, 84) / 100;
    const maximumHeight = editor.clientHeight * (customWidth ? 88 : limits.height) / 100;
    const aspectRatio = image.naturalWidth / image.naturalHeight;
    const fittedWidth = Math.min(maximumWidth, maximumHeight * aspectRatio);
    const fittedPercent = fittedWidth / editor.clientWidth * 100;
    wrapper.style.width = `${fittedPercent}%`;
    if (customWidth) {
      wrapper.dataset.imageWidth = compactCoordinate(fittedPercent);
    }
    return true;
  };

  const setImagePosition = (wrapper, xPercent, yPercent) => {
    const widthPercent = editor.clientWidth
      ? wrapper.offsetWidth / editor.clientWidth * 100
      : 0;
    const heightPercent = editor.clientHeight
      ? wrapper.offsetHeight / editor.clientHeight * 100
      : 0;
    const x = Math.max(0, Math.min(Math.max(0, 100 - widthPercent), xPercent));
    const y = Math.max(0, Math.min(Math.max(0, 100 - heightPercent), yPercent));
    wrapper.dataset.imageX = compactCoordinate(x);
    wrapper.dataset.imageY = compactCoordinate(y);
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

  const refreshImageLayout = wrapper => {
    fitImageToLabel(wrapper);
    applyImagePosition(wrapper);
  };

  const startImageResize = (event, wrapper, corner) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectImage(wrapper);
    wrapper.focus({ preventScroll: true });

    const image = wrapper.querySelector(".editor-image");
    if (!image || !image.naturalWidth || !image.naturalHeight) return;
    const editorRect = editor.getBoundingClientRect();
    const scaleX = editor.clientWidth / editorRect.width;
    const scaleY = editor.clientHeight / editorRect.height;
    const startLeft = wrapper.offsetLeft;
    const startTop = wrapper.offsetTop;
    const startWidth = wrapper.offsetWidth;
    const startHeight = wrapper.offsetHeight;
    const anchorX = corner.includes("w") ? startLeft + startWidth : startLeft;
    const anchorY = corner.includes("n") ? startTop + startHeight : startTop;
    const aspectRatio = image.naturalWidth / image.naturalHeight;
    const handle = event.currentTarget;
    handle.setPointerCapture(event.pointerId);

    const resize = moveEvent => {
      const pointerX = (moveEvent.clientX - editorRect.left) * scaleX;
      const pointerY = (moveEvent.clientY - editorRect.top) * scaleY;
      const distanceX = Math.abs(pointerX - anchorX);
      const distanceY = Math.abs(pointerY - anchorY);
      const projectedHeight = (distanceX * aspectRatio + distanceY) / (aspectRatio * aspectRatio + 1);
      const horizontalSpace = corner.includes("w") ? anchorX : editor.clientWidth - anchorX;
      const verticalSpace = corner.includes("n") ? anchorY : editor.clientHeight - anchorY;
      const maximumWidth = Math.max(1, Math.min(
        editor.clientWidth * 0.84,
        editor.clientHeight * 0.88 * aspectRatio,
        horizontalSpace,
        verticalSpace * aspectRatio
      ));
      const minimumWidth = Math.min(maximumWidth, Math.max(12, editor.clientWidth * 0.05));
      const width = Math.max(minimumWidth, Math.min(maximumWidth, projectedHeight * aspectRatio));
      const left = corner.includes("w") ? anchorX - width : anchorX;
      const top = corner.includes("n") ? anchorY - width / aspectRatio : anchorY;
      const widthPercent = width / editor.clientWidth * 100;

      wrapper.style.width = `${widthPercent}%`;
      wrapper.dataset.imageWidth = compactCoordinate(widthPercent);
      setImagePosition(
        wrapper,
        left / editor.clientWidth * 100,
        top / editor.clientHeight * 100
      );
    };
    const finish = () => {
      handle.removeEventListener("pointermove", resize);
      handle.removeEventListener("pointerup", finish);
      handle.removeEventListener("pointercancel", finish);
      selectImage(wrapper);
      saveDraft();
      updateOverflowState();
    };
    handle.addEventListener("pointermove", resize);
    handle.addEventListener("pointerup", finish);
    handle.addEventListener("pointercancel", finish);
  };

  const addImageResizeHandles = wrapper => {
    if (wrapper.querySelector(".image-resize-handle")) return;
    ["nw", "ne", "sw", "se"].forEach(corner => {
      const handle = document.createElement("span");
      handle.className = `image-resize-handle image-resize-${corner}`;
      handle.dataset.resizeCorner = corner;
      handle.setAttribute("aria-hidden", "true");
      handle.addEventListener("pointerdown", event => startImageResize(event, wrapper, corner));
      wrapper.append(handle);
    });
  };

  const prepareImageWrapper = wrapper => {
    if (!wrapper.dataset.imageSize) wrapper.dataset.imageSize = "medium";
    if (!wrapper.dataset.imageX) wrapper.dataset.imageX = "2.273";
    if (!wrapper.dataset.imageY) wrapper.dataset.imageY = "5.882";
    wrapper.contentEditable = "false";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("aria-label", t("Positioned image. Drag it or use the arrow keys to move it."));
    addImageResizeHandles(wrapper);
    refreshImageLayout(wrapper);
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

  const setTextPosition = (wrapper, xPercent, yPercent) => {
    const widthPercent = editor.clientWidth
      ? wrapper.offsetWidth / editor.clientWidth * 100
      : coordinate(wrapper.dataset.textWidth || "55");
    const heightPercent = editor.clientHeight
      ? wrapper.offsetHeight / editor.clientHeight * 100
      : 0;
    const x = Math.max(0, Math.min(Math.max(0, 100 - widthPercent), xPercent));
    const y = Math.max(0, Math.min(Math.max(0, 100 - heightPercent), yPercent));
    wrapper.dataset.textX = compactCoordinate(x);
    wrapper.dataset.textY = compactCoordinate(y);
    wrapper.style.left = `${x}%`;
    wrapper.style.top = `${y}%`;
  };

  const applyTextLayout = wrapper => {
    const requestedWidth = coordinate(wrapper.dataset.textWidth || "55");
    const requestedHeight = coordinate(wrapper.dataset.textHeight || "18");
    const x = coordinate(wrapper.dataset.textX || "2.273");
    const y = coordinate(wrapper.dataset.textY || "5.882");
    const maximumWidth = Math.max(15, 100 - x);
    const maximumHeight = Math.max(8, 100 - y);
    const width = Math.max(15, Math.min(maximumWidth, requestedWidth));
    const height = Math.max(8, Math.min(maximumHeight, requestedHeight));
    wrapper.dataset.textWidth = compactCoordinate(width);
    wrapper.dataset.textHeight = compactCoordinate(height);
    wrapper.style.width = `${width}%`;
    wrapper.style.height = `${height}%`;
    setTextPosition(
      wrapper,
      x,
      y
    );
  };

  const growTextBoxToContent = wrapper => {
    const textBox = wrapper.querySelector(".editor-text-box");
    if (!textBox || !editor.clientHeight) return;
    const requiredHeight = textBox.scrollHeight + 1;
    if (requiredHeight <= wrapper.clientHeight + 1) return;
    const maximumHeight = editor.clientHeight - wrapper.offsetTop;
    const height = Math.min(maximumHeight, requiredHeight);
    const heightPercent = height / editor.clientHeight * 100;
    wrapper.dataset.textHeight = compactCoordinate(heightPercent);
    wrapper.style.height = `${heightPercent}%`;
    setTextPosition(
      wrapper,
      coordinate(wrapper.dataset.textX),
      coordinate(wrapper.dataset.textY)
    );
  };

  const startTextMove = (event, wrapper) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectText(wrapper);
    const handle = event.currentTarget;
    const editorRect = editor.getBoundingClientRect();
    const scaleX = editor.clientWidth / editorRect.width;
    const scaleY = editor.clientHeight / editorRect.height;
    const startX = event.clientX;
    const startY = event.clientY;
    const startLeft = wrapper.offsetLeft;
    const startTop = wrapper.offsetTop;
    handle.setPointerCapture(event.pointerId);

    const move = moveEvent => {
      setTextPosition(
        wrapper,
        (startLeft + (moveEvent.clientX - startX) * scaleX) / editor.clientWidth * 100,
        (startTop + (moveEvent.clientY - startY) * scaleY) / editor.clientHeight * 100
      );
    };
    const finish = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", finish);
      handle.removeEventListener("pointercancel", finish);
      saveDraft();
      updateOverflowState();
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", finish);
    handle.addEventListener("pointercancel", finish);
  };

  const startTextResize = (event, wrapper, corner) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectText(wrapper);
    const handle = event.currentTarget;
    const editorRect = editor.getBoundingClientRect();
    const scaleX = editor.clientWidth / editorRect.width;
    const scaleY = editor.clientHeight / editorRect.height;
    const startLeft = wrapper.offsetLeft;
    const startTop = wrapper.offsetTop;
    const startWidth = wrapper.offsetWidth;
    const startHeight = wrapper.offsetHeight;
    const anchorX = corner.includes("w") ? startLeft + startWidth : startLeft;
    const anchorY = corner.includes("n") ? startTop + startHeight : startTop;
    const minimumWidth = editor.clientWidth * 0.15;
    const minimumHeight = editor.clientHeight * 0.08;
    handle.setPointerCapture(event.pointerId);

    const resize = moveEvent => {
      const pointerX = (moveEvent.clientX - editorRect.left) * scaleX;
      const pointerY = (moveEvent.clientY - editorRect.top) * scaleY;
      const maximumWidth = corner.includes("w") ? anchorX : editor.clientWidth - anchorX;
      const maximumHeight = corner.includes("n") ? anchorY : editor.clientHeight - anchorY;
      const width = Math.max(
        Math.min(minimumWidth, maximumWidth),
        Math.min(maximumWidth, Math.abs(pointerX - anchorX))
      );
      const height = Math.max(
        Math.min(minimumHeight, maximumHeight),
        Math.min(maximumHeight, Math.abs(pointerY - anchorY))
      );
      const left = corner.includes("w") ? anchorX - width : anchorX;
      const top = corner.includes("n") ? anchorY - height : anchorY;
      const widthPercent = width / editor.clientWidth * 100;
      const heightPercent = height / editor.clientHeight * 100;
      wrapper.dataset.textWidth = compactCoordinate(widthPercent);
      wrapper.dataset.textHeight = compactCoordinate(heightPercent);
      wrapper.style.width = `${widthPercent}%`;
      wrapper.style.height = `${heightPercent}%`;
      setTextPosition(
        wrapper,
        left / editor.clientWidth * 100,
        top / editor.clientHeight * 100
      );
      growTextBoxToContent(wrapper);
    };
    const finish = () => {
      handle.removeEventListener("pointermove", resize);
      handle.removeEventListener("pointerup", finish);
      handle.removeEventListener("pointercancel", finish);
      growTextBoxToContent(wrapper);
      saveDraft();
      updateOverflowState();
    };
    handle.addEventListener("pointermove", resize);
    handle.addEventListener("pointerup", finish);
    handle.addEventListener("pointercancel", finish);
  };

  const addTextControls = wrapper => {
    if (wrapper.querySelector(".text-box-control")) return;
    const moveHandle = document.createElement("button");
    moveHandle.className = "text-box-control text-move-handle";
    moveHandle.type = "button";
    moveHandle.contentEditable = "false";
    moveHandle.setAttribute("aria-label", t("Move text box"));
    moveHandle.title = t("Move text box");
    moveHandle.innerHTML = '<i class="fas fa-arrows-alt" aria-hidden="true"></i>';
    moveHandle.addEventListener("pointerdown", event => startTextMove(event, wrapper));
    moveHandle.addEventListener("keydown", event => {
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
      setTextPosition(
        wrapper,
        (wrapper.offsetLeft + horizontal * stepPx) / editor.clientWidth * 100,
        (wrapper.offsetTop + vertical * stepPx) / editor.clientHeight * 100
      );
      saveDraft();
    });

    wrapper.append(moveHandle);
    ["nw", "ne", "sw", "se"].forEach(corner => {
      const resizeHandle = document.createElement("span");
      resizeHandle.className = `text-box-control text-resize-handle text-resize-${corner}`;
      resizeHandle.dataset.resizeCorner = corner;
      resizeHandle.contentEditable = "false";
      resizeHandle.setAttribute("aria-hidden", "true");
      resizeHandle.addEventListener("pointerdown", event => startTextResize(event, wrapper, corner));
      wrapper.append(resizeHandle);
    });
  };

  const prepareTextWrapper = wrapper => {
    if (!wrapper.dataset.textX) wrapper.dataset.textX = "2.273";
    if (!wrapper.dataset.textY) wrapper.dataset.textY = "5.882";
    if (!wrapper.dataset.textWidth) wrapper.dataset.textWidth = "55";
    if (!wrapper.dataset.textHeight) wrapper.dataset.textHeight = "18";
    wrapper.contentEditable = "false";
    let textBox = wrapper.querySelector(":scope > .editor-text-box");
    if (!textBox) {
      textBox = document.createElement("div");
      textBox.className = "editor-text-box";
      wrapper.prepend(textBox);
    }
    textBox.contentEditable = "true";
    textBox.spellcheck = true;
    textBox.setAttribute("role", "textbox");
    textBox.setAttribute("aria-multiline", "true");
    textBox.setAttribute("aria-label", t("Label text box"));
    addTextControls(wrapper);
    applyTextLayout(wrapper);
    requestAnimationFrame(() => growTextBoxToContent(wrapper));
    if (wrapper._textPositioningReady) return;
    wrapper._textPositioningReady = true;
    wrapper.addEventListener("pointerdown", event => {
      if (event.target.closest(".text-box-control")) return;
      selectText(wrapper);
    });
    textBox.addEventListener("focus", () => selectText(wrapper));
  };

  const focusTextBox = wrapper => {
    const textBox = wrapper.querySelector(".editor-text-box");
    selectText(wrapper);
    textBox.focus({ preventScroll: true });
    const range = document.createRange();
    range.selectNodeContents(textBox);
    range.collapse(false);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    savedRange = range.cloneRange();
  };

  const createTextBox = ({ x, y, width = 55, height = 18, focus = true } = {}) => {
    const count = editor.querySelectorAll(".editor-text-wrap").length;
    const wrapper = document.createElement("div");
    wrapper.className = "editor-text-wrap";
    wrapper.dataset.textX = String(x !== undefined ? x : (2.273 + (count * 4) % 28));
    wrapper.dataset.textY = String(y !== undefined ? y : (5.882 + (count * 13) % 62));
    wrapper.dataset.textWidth = String(width);
    wrapper.dataset.textHeight = String(height);
    const textBox = document.createElement("div");
    textBox.className = "editor-text-box";
    wrapper.append(textBox);
    editor.append(wrapper);
    prepareTextWrapper(wrapper);
    if (focus) focusTextBox(wrapper);
    updateEmptyState();
    return wrapper;
  };

  const migrateLegacyText = () => {
    if (editor.querySelector(".editor-text-wrap")) return;
    const legacyNodes = Array.from(editor.childNodes).filter(node =>
      !(node.nodeType === Node.ELEMENT_NODE && node.classList.contains("editor-image-wrap"))
    );
    const containsText = legacyNodes.some(node =>
      node.textContent.replace(/\u00a0/g, " ").trim() ||
      (node.nodeType === Node.ELEMENT_NODE && node.querySelector("br")) ||
      (node.nodeType === Node.ELEMENT_NODE && node.tagName === "BR")
    );
    if (!containsText) {
      legacyNodes.forEach(node => node.remove());
      return;
    }
    const wrapper = createTextBox({ width: 95.454, focus: false });
    const textBox = wrapper.querySelector(".editor-text-box");
    textBox.replaceChildren(...legacyNodes);
  };

  const updateOverflowState = () => {
    const overflows =
      editor.scrollHeight > editor.clientHeight + 2 ||
      editor.scrollWidth > editor.clientWidth + 2;
    editor.classList.toggle("is-overflowing", overflows);
    editor.setAttribute("aria-invalid", overflows ? "true" : "false");
    updateEmptyState();
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
    }
    migrateLegacyText();
    editor.querySelectorAll(".editor-text-wrap").forEach(prepareTextWrapper);
    editor.querySelectorAll(".editor-image-wrap").forEach(prepareImageWrapper);
    editor.querySelectorAll(".editor-image").forEach(image => {
      const refreshLoadedImage = () => {
        refreshImageLayout(image.closest(".editor-image-wrap"));
        updateOverflowState();
      };
      if (image.complete && image.naturalWidth) refreshLoadedImage();
      else image.addEventListener("load", refreshLoadedImage, { once: true });
    });
  } catch (_error) {
    // Ignore unavailable storage.
  }
  if (!editor.querySelector(".editor-text-wrap") && !hasImage()) {
    createTextBox();
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
    const wrapper = document.activeElement.closest && document.activeElement.closest(".editor-text-wrap");
    if (wrapper) {
      growTextBoxToContent(wrapper);
    }
    updateOverflowState();
    saveDraft();
  });

  const imageFromFile = async file => {
    if (file.size > 20 * 1024 * 1024) {
      throw new Error(t("The selected image is too large."));
    }
    const objectUrl = URL.createObjectURL(file);
    const source = new Image();
    try {
      await new Promise((resolve, reject) => {
        source.onload = resolve;
        source.onerror = () => reject(new Error(t("The selected image could not be read.")));
        source.src = objectUrl;
      });

      if (source.naturalWidth * source.naturalHeight > 40_000_000) {
        throw new Error(t("The clipboard image contains too many pixels."));
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

  const insertImage = (source, size = "medium") => {
    const wrapper = document.createElement("span");
    wrapper.className = "editor-image-wrap";
    wrapper.dataset.imageSize = size;
    wrapper.dataset.imageX = "2.273";
    wrapper.dataset.imageY = "5.882";
    wrapper.contentEditable = "false";

    const image = document.createElement("img");
    image.className = "editor-image";
    image.alt = t("Pasted image");
    image.draggable = false;
    image.addEventListener("load", () => {
      refreshImageLayout(wrapper);
      updateOverflowState();
    }, { once: true });
    image.src = source;
    wrapper.append(image);
    editor.append(wrapper);
    prepareImageWrapper(wrapper);
    selectImage(wrapper);
    hideError();
    saveDraft();
    updateOverflowState();
  };

  const setSymbolPaletteOpen = open => {
    symbolPalette.hidden = !open;
    insertSymbolButton.setAttribute("aria-expanded", open ? "true" : "false");
  };

  const renderSymbolImage = async glyphCode => {
    const glyph = String.fromCodePoint(Number.parseInt(glyphCode, 16));
    const font = '900 176px "Font Awesome 5 Free"';
    if (document.fonts) await document.fonts.load(font, glyph);
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const symbolContext = canvas.getContext("2d");
    symbolContext.clearRect(0, 0, canvas.width, canvas.height);
    symbolContext.fillStyle = "#000";
    symbolContext.font = font;
    symbolContext.textAlign = "left";
    symbolContext.textBaseline = "alphabetic";
    const metrics = symbolContext.measureText(glyph);
    const left = metrics.actualBoundingBoxLeft || 0;
    const right = metrics.actualBoundingBoxRight || metrics.width;
    const ascent = metrics.actualBoundingBoxAscent || 176;
    const descent = metrics.actualBoundingBoxDescent || 0;
    const x = (canvas.width - left - right) / 2 + left;
    const y = (canvas.height - ascent - descent) / 2 + ascent;
    symbolContext.fillText(glyph, x, y);
    return canvas.toDataURL("image/png");
  };

  insertSymbolButton.addEventListener("click", () => {
    setSymbolPaletteOpen(symbolPalette.hidden);
  });
  closeSymbolPaletteButton.addEventListener("click", () => setSymbolPaletteOpen(false));
  symbolChoices.forEach(button => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        insertImage(await renderSymbolImage(button.dataset.symbolGlyph), "small");
        setSymbolPaletteOpen(false);
      } catch (_error) {
        showError(t("The symbol could not be inserted."));
      } finally {
        button.disabled = false;
      }
    });
  });
  document.addEventListener("click", event => {
    if (
      !symbolPalette.hidden &&
      !symbolPalette.contains(event.target) &&
      !insertSymbolButton.contains(event.target)
    ) {
      setSymbolPaletteOpen(false);
    }
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !symbolPalette.hidden) {
      setSymbolPaletteOpen(false);
      insertSymbolButton.focus();
    }
  });

  editor.addEventListener("paste", async event => {
    const imageItem = Array.from(event.clipboardData.items || []).find(item =>
      item.type.startsWith("image/")
    );
    if (imageItem) {
      event.preventDefault();
      rememberSelection();
      try {
        const file = imageItem.getAsFile();
        if (!file) throw new Error(t("No readable image was found on the clipboard."));
        insertImage(await imageFromFile(file));
      } catch (error) {
        showError(error.message || t("The image could not be pasted."));
      }
      return;
    }

    event.preventDefault();
    const text = event.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  });

  editor.addEventListener("click", event => {
    const imageWrapper = event.target.closest(".editor-image-wrap");
    if (imageWrapper && editor.contains(imageWrapper)) {
      selectImage(imageWrapper);
      return;
    }
    const textWrapper = event.target.closest(".editor-text-wrap");
    if (textWrapper && editor.contains(textWrapper)) {
      selectText(textWrapper);
      return;
    }
    selectImage(null);
  });

  insertTextButton.addEventListener("click", () => {
    const wrapper = Array.from(editor.querySelectorAll(".editor-text-wrap")).find(candidate => {
      const textBox = candidate.querySelector(".editor-text-box");
      return textBox && !textBox.textContent.replace(/\u00a0/g, " ").trim();
    }) || createTextBox({ focus: false });
    hideError();
    saveDraft();
    updateOverflowState();
    focusTextBox(wrapper);
  });
  insertImageButton.addEventListener("click", () => imageFile.click());
  imageFile.addEventListener("change", async () => {
    const file = imageFile.files && imageFile.files[0];
    if (!file) return;
    try {
      insertImage(await imageFromFile(file));
    } catch (error) {
      showError(error.message || t("The image could not be inserted."));
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

  const setFontPickerOpen = open => {
    fontPickerMenu.hidden = !open;
    fontPickerButton.setAttribute("aria-expanded", open ? "true" : "false");
  };

  fontPickerButton.addEventListener("pointerdown", rememberSelection);
  fontPickerButton.addEventListener("click", () => {
    const open = fontPickerMenu.hidden;
    setFontPickerOpen(open);
    const selectedOption = fontPickerMenu.querySelector('[aria-selected="true"]');
    if (open && selectedOption) selectedOption.focus();
  });
  fontPickerOptions.forEach(option => {
    option.addEventListener("pointerdown", event => event.preventDefault());
    option.addEventListener("click", () => {
      restoreSelection();
      document.execCommand("fontName", false, option.dataset.fontFamily);
      fontPickerOptions.forEach(candidate =>
        candidate.setAttribute("aria-selected", candidate === option ? "true" : "false")
      );
      fontPickerLabel.textContent = option.textContent;
      fontPickerLabel.className = option.dataset.fontPreview;
      setFontPickerOpen(false);
      rememberSelection();
      saveDraft();
      updateOverflowState();
    });
  });
  fontPickerMenu.addEventListener("keydown", event => {
    const options = Array.from(fontPickerOptions);
    const index = options.indexOf(document.activeElement);
    if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      options[(index + direction + options.length) % options.length].focus();
    } else if (event.key === "Escape") {
      setFontPickerOpen(false);
      fontPickerButton.focus();
    }
  });
  document.addEventListener("click", event => {
    if (!fontPickerMenu.hidden && !fontPicker.contains(event.target)) {
      setFontPickerOpen(false);
    }
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
    if (hasContent() && !window.confirm(t("Clear the current label?"))) return;
    setSymbolPaletteOpen(false);
    editor.replaceChildren();
    savedRange = null;
    selectImage(null);
    const wrapper = createTextBox({ focus: false });
    saveDraft();
    updateOverflowState();
    hideError();
    focusTextBox(wrapper);
  });

  deleteSelectedButton.addEventListener("click", () => {
    if (selectedImage) {
      const wrapper = selectedImage;
      selectImage(null);
      wrapper.remove();
      if (!editor.querySelector(".editor-text-wrap") && !hasImage()) {
        createTextBox({ focus: false });
      }
    } else if (selectedText) {
      const wrapper = selectedText;
      savedRange = null;
      selectText(null);
      wrapper.remove();
      let nextText = editor.querySelector(".editor-text-wrap");
      if (!nextText && !hasImage()) nextText = createTextBox({ focus: false });
      if (nextText) focusTextBox(nextText);
    } else {
      return;
    }
    saveDraft();
    updateOverflowState();
  });

  const renderToCanvas = async () => {
    if (typeof window.html2canvas !== "function") {
      throw new Error(t("The print renderer did not load. Reload the page and try again."));
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
        clonedEditor.querySelectorAll("[contenteditable]").forEach(node => node.removeAttribute("contenteditable"));
        clonedEditor.querySelectorAll(".image-resize-handle,.text-box-control").forEach(node => node.remove());
        clonedEditor.querySelectorAll(".is-selected").forEach(node => {
          node.classList.remove("is-selected");
        });
      },
    });
    if (Math.abs(renderedEditor.width - outputWidth) > 1 || Math.abs(renderedEditor.height - outputHeight) > 1) {
      throw new Error(t("The browser did not create an exact-size print image."));
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
        image.addEventListener("error", () => reject(new Error(t("A pasted image could not be loaded."))), { once: true });
      });
    })
  );

  const canvasBlob = canvas => new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(new Error(t("The print preview could not be created.")));
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
      showError(t("Enter text or paste an image from the clipboard."));
      const textBox = editor.querySelector(".editor-text-wrap") || createTextBox({ focus: false });
      focusTextBox(textBox);
      return;
    }
    if (text.length > 2000) {
      showError(t("The text is too long."));
      return;
    }
    if (updateOverflowState()) {
      showError(t("The content extends beyond the printable area. Make it smaller."));
      return;
    }

    submitting = true;
    submitButton.disabled = true;
    saveButton.disabled = true;
    submitButton.classList.add("is-loading");
    if (activeButton === saveButton) {
      saveButtonLabel.textContent = t("Saving…");
    } else {
      submitButtonLabel.textContent = t("Creating preview…");
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
        throw new Error(payload.error || t("The label could not be created."));
      }
      localStorage.removeItem(storageKey);
      window.location.assign(payload.redirect_url);
    } catch (error) {
      submitting = false;
      submitButton.disabled = false;
      saveButton.disabled = false;
      submitButton.classList.remove("is-loading");
      submitButtonLabel.textContent = t("Continue to print");
      saveButtonLabel.textContent = t("Save");
      showError(error.message || t("The label could not be created."));
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
