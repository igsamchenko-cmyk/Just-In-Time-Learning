document.addEventListener("DOMContentLoaded", () => {
  const loadingForms = document.querySelectorAll("form[data-loading-text]");

  loadingForms.forEach((form) => {
    form.addEventListener("submit", () => {
      const loadingText = form.dataset.loadingText || "Зачекай...";
      const buttons = form.querySelectorAll("button");
      const fields = form.querySelectorAll("input, textarea, select");

      buttons.forEach((button) => {
        if (!button.dataset.originalText) {
          button.dataset.originalText = button.textContent || "";
        }
        button.textContent = loadingText;
        button.disabled = true;
        button.classList.add("is-loading");
      });

      fields.forEach((field) => {
        field.readOnly = true;
      });

      if (!form.querySelector(".loading-note")) {
        const note = document.createElement("p");
        note.className = "loading-note";
        note.textContent = loadingText;
        form.appendChild(note);
      }
    });
  });
});
