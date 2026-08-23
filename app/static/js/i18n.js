(() => {
  "use strict";

  const translations = window.APP_TRANSLATIONS || {};
  window.appT = (message, values = {}) => {
    const translated = translations[message] || message;
    return translated.replace(/\{([A-Za-z0-9_]+)\}/g, (match, key) => (
      Object.prototype.hasOwnProperty.call(values, key) ? String(values[key]) : match
    ));
  };
})();
