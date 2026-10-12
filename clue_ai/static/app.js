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

  const progressPanel = document.querySelector("[data-preparation-progress]");
  if (progressPanel) {
    const message = progressPanel.querySelector("[data-progress-message]");
    const stateLabel = progressPanel.querySelector("[data-progress-state]");
    const timing = progressPanel.querySelector("[data-progress-timing]");
    const progressBar = progressPanel.querySelector("[data-progress-bar]");
    const stallWarning = progressPanel.querySelector("[data-progress-stall]");
    const connectionWarning = progressPanel.querySelector("[data-progress-connection]");
    const queueLabel = progressPanel.querySelector("[data-progress-queue]");
    const progressUrl = progressPanel.dataset.progressUrl || "";
    const pollInterval = Math.max(1000, Number(progressPanel.dataset.pollIntervalMs) || 2500);
    const staleAfter = Math.max(15, Number(progressPanel.dataset.staleAfterSeconds) || 35);
    const steps = [...progressPanel.querySelectorAll("[data-progress-step]")];
    let state = progressPanel.dataset.state || "";
    let createdAt = progressPanel.dataset.createdAt || "";
    let lastUpdatedAt = progressPanel.dataset.updatedAt || "";
    let heartbeatAt = progressPanel.dataset.workerHeartbeatAt || "";
    let pollTimer = null;
    let clockTimer = null;

    const stateNames = {
      requested: "Queued",
      researching: "Researching",
      generating: "Generating and checking",
      review: "Ready for review",
      completed: "Owner approved",
      blocked: "Blocked",
      failed: "Needs attention",
      cancelled: "Cancelled",
    };
    const activeStates = new Set(["requested", "researching", "generating"]);
    const parseTime = (value) => {
      const parsed = value ? Date.parse(value) : NaN;
      return Number.isFinite(parsed) ? parsed : 0;
    };
    const durationLabel = (totalSeconds) => {
      const seconds = Math.max(0, Math.floor(totalSeconds));
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainder = seconds % 60;
      if (hours) return `${hours}h ${minutes}m`;
      if (minutes) return `${minutes}m ${remainder}s`;
      return `${remainder}s`;
    };
    const setTextIfChanged = (node, value) => {
      if (node && node.textContent !== value) node.textContent = value;
    };
    const updateTiming = () => {
      if (!timing || !activeStates.has(state)) return;
      const now = Date.now();
      const start = parseTime(createdAt);
      const heartbeat = parseTime(heartbeatAt);
      const lastUpdate = parseTime(lastUpdatedAt);
      const elapsed = start ? durationLabel((now - start) / 1000) : "—";
      const signalTime = heartbeat || lastUpdate;
      const signalAge = signalTime ? Math.max(0, Math.floor((now - signalTime) / 1000)) : null;
      const heartbeatLabel = heartbeat
        ? `Last worker heartbeat ${durationLabel(signalAge)} ago.`
        : "Waiting for the first worker heartbeat.";
      setTextIfChanged(timing, `Elapsed ${elapsed}. ${heartbeatLabel}`);
      if (stallWarning) {
        const stale = signalAge === null ? (start > 0 && (now - start) / 1000 > staleAfter) : signalAge > staleAfter;
        stallWarning.hidden = !stale;
        if (stale) {
          stallWarning.textContent = `No worker heartbeat for ${signalAge === null ? "more than " : ""}${signalAge === null ? staleAfter : signalAge} seconds. Preparation may have stalled or stopped; check the local Clue process before retrying.`;
        }
      }
    };
    const renderProgress = (payload) => {
      state = payload.state || state;
      createdAt = payload.created_at || createdAt;
      lastUpdatedAt = payload.updated_at || lastUpdatedAt;
      heartbeatAt = payload.worker_heartbeat_at || heartbeatAt;
      progressPanel.dataset.state = state;
      progressPanel.dataset.updatedAt = lastUpdatedAt;
      progressPanel.dataset.workerHeartbeatAt = heartbeatAt;
      progressPanel.setAttribute("aria-busy", payload.active ? "true" : "false");
      setTextIfChanged(message, payload.status_message || "Preparation status updated.");
      setTextIfChanged(stateLabel, stateNames[state] || state);
      if (queueLabel) queueLabel.hidden = state !== "requested";
      if (progressBar) progressBar.hidden = !payload.active;
      const stepIndex = Number.isInteger(payload.step_index) ? payload.step_index : null;
      steps.forEach((step) => {
        const index = Number(step.dataset.progressStep);
        const complete = (stepIndex !== null && index < stepIndex)
          || ((state === "review" || state === "completed") && index === 3)
          || (state === "completed" && index < 3);
        const current = payload.active && stepIndex === index;
        step.classList.toggle("is-complete", complete);
        step.classList.toggle("is-active", current);
        if (current) step.setAttribute("aria-current", "step");
        else step.removeAttribute("aria-current");
      });
      if (connectionWarning) connectionWarning.hidden = true;
      updateTiming();
      if (!payload.active) {
        if (pollTimer) window.clearTimeout(pollTimer);
        if (clockTimer) window.clearInterval(clockTimer);
        pollTimer = null;
        clockTimer = null;
      }
    };

    const poll = async () => {
      if (!progressUrl || !activeStates.has(state)) return;
      try {
        const response = await fetch(progressUrl, {
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Status request returned ${response.status}`);
        renderProgress(await response.json());
      } catch (_error) {
        if (connectionWarning) {
          connectionWarning.hidden = false;
          connectionWarning.textContent = "Clue did not respond to the progress check. Keep the local app running; its current state cannot be confirmed yet.";
        }
      }
      if (activeStates.has(state)) pollTimer = window.setTimeout(poll, pollInterval);
    };

    if (progressUrl && activeStates.has(state)) {
      updateTiming();
      clockTimer = window.setInterval(updateTiming, 1000);
      pollTimer = window.setTimeout(poll, 500);
    }
  }
})();
