(() => {
  const t = window.appT || (message => message);
  const modal = document.getElementById("labelActionModal");
  if (!modal) return;

  const image = document.getElementById("modalLabelImage");
  const prompt = document.getElementById("labelModalTitle");
  const format = document.getElementById("modalLabelFormat");
  const printForm = document.getElementById("modalPrintForm");
  const deleteForm = document.getElementById("modalDeleteForm");
  const editLink = document.getElementById("modalEditLink");
  const copyLink = document.getElementById("modalCopyLink");

  deleteForm.addEventListener("submit", event => {
    if (!window.confirm(t("Delete this saved label?"))) event.preventDefault();
  });

  modal.addEventListener("show.bs.modal", event => {
    const trigger = event.relatedTarget;
    const card = trigger && typeof trigger.closest === "function"
      ? trigger.closest(".gallery-card")
      : trigger;
    if (!card) return;

    const thumbnail = typeof card.querySelector === "function"
      ? card.querySelector("img")
      : null;
    const imageUrl = card.dataset.imageUrl
      || (thumbnail && (thumbnail.currentSrc || thumbnail.src));

    if (imageUrl) {
      image.src = new URL(imageUrl, document.baseURI).href;
    } else {
      image.removeAttribute("src");
    }
    image.alt = card.dataset.prompt || "";
    prompt.textContent = card.dataset.prompt || "";
    format.textContent = card.dataset.format || "";
    printForm.action = card.dataset.printUrl || "";
    deleteForm.action = card.dataset.deleteUrl || "";
    if (editLink) editLink.href = card.dataset.editUrl || "";
    if (copyLink) copyLink.href = card.dataset.copyUrl || "";
  });

  modal.addEventListener("hidden.bs.modal", () => {
    image.removeAttribute("src");
    image.alt = "";
    prompt.textContent = "";
    format.textContent = "";
    printForm.removeAttribute("action");
    deleteForm.removeAttribute("action");
    if (editLink) editLink.removeAttribute("href");
    if (copyLink) copyLink.removeAttribute("href");
  });
})();
