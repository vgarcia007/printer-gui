(() => {
  "use strict";

  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js", {scope: "/"}).catch((error) => {
      console.warn("The Print & Scan Hub service worker could not be registered.", error);
    });
  });
})();
