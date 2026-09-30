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
  const careerField = document.querySelector('[data-source-field="career-url"]');
  const identifierLabel = document.querySelector("#source-identifier-label");
  const identifierHelp = document.querySelector("#source-identifier-help");
  const updateSourceFields = () => {
    if (!sourceType || !identifierField || !careerField) return;
    const isCareerPage = sourceType.value === "scrapling";
    identifierField.hidden = isCareerPage;
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
})();
