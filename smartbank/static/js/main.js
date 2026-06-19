/* SmartBank – main.js */

// ── Theme toggle ─────────────────────────────────────────────────────────────
(function () {
  const html = document.documentElement;
  const saved = localStorage.getItem("sb_theme") || "dark";
  html.setAttribute("data-theme", saved);

  const btn  = document.getElementById("themeToggle");
  const icon = document.getElementById("themeIcon");

  function applyTheme(t) {
    html.setAttribute("data-theme", t);
    localStorage.setItem("sb_theme", t);
    if (icon) {
      icon.className = t === "dark" ? "bi bi-moon-stars-fill" : "bi bi-sun-fill";
    }
  }

  applyTheme(saved);

  if (btn) {
    btn.addEventListener("click", () => {
      const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }
})();

// ── Auto-dismiss flash alerts after 4s ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sb-alert").forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 4000);
  });
});
