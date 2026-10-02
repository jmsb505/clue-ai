(() => {
  const statusUrl = document.body.dataset.statusUrl;
  if (!statusUrl) return;
  const progressMessage = document.querySelector(".progress-message");
  let stopped = false;
  const poll = async () => {
    if (stopped) return;
    try {
      const response = await fetch(statusUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const state = await response.json();
      if (progressMessage && state.message) progressMessage.textContent = state.message;
      if (state.status === "complete" || state.status === "failed") {
        stopped = true;
        window.location.reload();
        return;
      }
    } catch (_error) {
      // A local refresh can temporarily interrupt polling; the user can still reload.
    }
    window.setTimeout(poll, 1800);
  };
  window.setTimeout(poll, 1200);
})();
