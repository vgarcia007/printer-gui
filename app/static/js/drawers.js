(() => {
  const t = window.appT || (message => message);
  const triggers = [...document.querySelectorAll("[data-drawer-trigger]")];
  triggers.forEach(trigger => {
    const drawer = document.getElementById(trigger.getAttribute("aria-controls"));
    if (!drawer) return;
    const scrim = document.querySelector(`[data-drawer-scrim="${drawer.id}"]`);
    const close = drawer.querySelector("[data-drawer-close]");
    if (!scrim || !close) return;
    let hideScrimTimer = null;
    const setOpen = value => {
      drawer.classList.toggle("open", value);
      drawer.setAttribute("aria-hidden", String(!value));
      trigger.setAttribute("aria-expanded", String(value));
      document.body.classList.toggle("drawer-open", value);
      if (value) {
        window.clearTimeout(hideScrimTimer);
        scrim.hidden = false;
        requestAnimationFrame(() => scrim.classList.add("open"));
        close.focus({ preventScroll: true });
        drawer.dispatchEvent(new CustomEvent("drawer:opened"));
      } else {
        scrim.classList.remove("open");
        hideScrimTimer = window.setTimeout(() => { scrim.hidden = true; }, 180);
        trigger.focus({ preventScroll: true });
      }
    };
    trigger.addEventListener("click", () => setOpen(true));
    close.addEventListener("click", () => setOpen(false));
    scrim.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && drawer.classList.contains("open")) setOpen(false);
    });
  });
  document.querySelectorAll("[data-confirm-label-delete]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(t("Delete this saved label?"))) event.preventDefault();
    });
  });
})();
