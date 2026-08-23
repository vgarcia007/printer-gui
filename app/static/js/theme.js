(() => {
  const storageKey = "print-scan-hub-theme";
  const root = document.documentElement;

  const storedTheme = (() => {
    try {
      return window.localStorage.getItem(storageKey);
    } catch (_error) {
      return null;
    }
  })();
  const initialTheme = storedTheme === "light" ? "light" : "dark";
  root.dataset.theme = initialTheme;
  root.style.colorScheme = initialTheme;

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("themeToggle");
    const icon = document.getElementById("themeToggleIcon");
    if (!toggle || !icon) return;

    const applyTheme = (theme, save) => {
      const isLight = theme === "light";
      root.dataset.theme = isLight ? "light" : "dark";
      root.style.colorScheme = isLight ? "light" : "dark";
      toggle.setAttribute("aria-checked", String(isLight));
      toggle.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
      toggle.title = isLight ? "Switch to dark mode" : "Switch to light mode";
      icon.className = isLight ? "fas fa-sun" : "fas fa-moon";

      const themeColor = document.querySelector('meta[name="theme-color"]');
      if (themeColor) themeColor.content = isLight ? "#f4f5f7" : "#212529";

      if (save) {
        try {
          window.localStorage.setItem(storageKey, isLight ? "light" : "dark");
        } catch (_error) {
          // The selected theme still applies when browser storage is unavailable.
        }
      }
    };

    applyTheme(initialTheme, false);
    toggle.addEventListener("click", () => {
      applyTheme(root.dataset.theme === "light" ? "dark" : "light", true);
    });
  });
})();
