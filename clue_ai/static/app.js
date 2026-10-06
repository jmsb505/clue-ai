(() => {
  const fileInput = document.querySelector("#cv-file");
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      const label = fileInput.closest(".file-picker");
      const name = fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "";
      const title = label && label.querySelector("b");
      if (title && name) title.textContent = name;
    });
  }

  const sourceType = document.querySelector("#source-kind");
  const identifierField = document.querySelector('[data-source-field="identifier"]');
  const leverRegionField = document.querySelector('[data-source-field="lever-region"]');
  const careerField = document.querySelector('[data-source-field="career-url"]');
  const identifierLabel = document.querySelector("#source-identifier-label");
  const identifierHelp = document.querySelector("#source-identifier-help");
  const updateSourceFields = () => {
    if (!sourceType || !identifierField || !leverRegionField || !careerField) return;
    const isCareerPage = sourceType.value === "scrapling";
    identifierField.hidden = isCareerPage;
    leverRegionField.hidden = sourceType.value !== "lever";
    careerField.hidden = !isCareerPage;
    const labels = {
      greenhouse: ["Greenhouse board token", "Use the token from the company's public Greenhouse board URL."],
      lever: ["Lever site identifier", "Use the slug from the company's public Lever board URL."],
      smartrecruiters: ["SmartRecruiters company identifier", "Use the identifier from the public company job board."],
    };
    if (!isCareerPage && labels[sourceType.value]) {
      identifierLabel.textContent = labels[sourceType.value][0];
      identifierHelp.textContent = labels[sourceType.value][1];
    }
  };
  if (sourceType) {
    sourceType.addEventListener("change", updateSourceFields);
    updateSourceFields();
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm");
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copyTarget || "");
      const card = button.closest(".packet-outreach-card");
      const status = card && card.querySelector("[data-copy-status]");
      if (!target || !status) return;
      const value = "value" in target ? target.value : target.textContent;
      if (!value) {
        status.textContent = "There is no text to copy.";
        return;
      }
      try {
        if (!navigator.clipboard || !window.isSecureContext) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(value);
        status.textContent = `Copied ${button.dataset.copyLabel || "text"}.`;
      } catch (_error) {
        target.focus();
        if (typeof target.select === "function") target.select();
        status.textContent = `Copy was unavailable. The ${button.dataset.copyLabel || "text"} is selected; use your keyboard's copy shortcut.`;
      }
    });
  });
})();
