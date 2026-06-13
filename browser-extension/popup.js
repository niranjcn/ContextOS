(function () {
  "use strict";

  const statusDot = document.getElementById("statusDot");
  const statusLabel = document.getElementById("statusLabel");
  const autoCaptureCheck = document.getElementById("autoCapture");
  const apiUrlInput = document.getElementById("apiUrl");
  const captureNowBtn = document.getElementById("captureNow");
  const clearBtn = document.getElementById("clearBtn");
  const capturesList = document.getElementById("capturesList");
  const emptyState = document.getElementById("emptyState");

  let currentCapures = [];

  async function loadSettings() {
    const { apiUrl, autoCapture } = await chrome.storage.local.get({
      apiUrl: "http://localhost:8000",
      autoCapture: true,
    });
    apiUrlInput.value = apiUrl;
    autoCaptureCheck.checked = autoCapture;
  }

  async function saveSettings() {
    await chrome.storage.local.set({
      apiUrl: apiUrlInput.value.trim() || "http://localhost:8000",
      autoCapture: autoCaptureCheck.checked,
    });
  }

  apiUrlInput.addEventListener("change", saveSettings);
  autoCaptureCheck.addEventListener("change", saveSettings);

  async function loadCaptures() {
    const { captures = [] } = await chrome.storage.local.get("captures");
    currentCapures = captures;
    renderCaptures(captures);
  }

  function renderCaptures(captures) {
    capturesList.innerHTML = "";

    if (captures.length === 0) {
      emptyState.style.display = "block";
      return;
    }
    emptyState.style.display = "none";

    for (const c of captures) {
      const li = document.createElement("li");
      li.className = "capture-item";

      const statusClass = c.sent ? "sent" : c.error ? "error" : "pending";
      const statusIcon = c.sent ? "\u2713" : c.error ? "\u2717" : "\u25CB";

      const time = new Date(c.capturedAt);
      const timeStr = time.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });

      li.innerHTML =
        '<span class="capture-status ' +
        statusClass +
        '">' +
        statusIcon +
        '</span>' +
        '<div class="capture-info">' +
        '<div class="capture-title" title="' +
        esc(c.title) +
        '">' +
        esc(c.title || "Untitled") +
        '</div>' +
        '<div class="capture-url" title="' +
        esc(c.url) +
        '">' +
        esc(c.url) +
        '</div>' +
        '<div class="capture-time">' +
        timeStr +
        (c.error ? ' &middot; <span style="color:#f87171">' + esc(c.error) + "</span>" : "") +
        "</div>" +
        "</div>";

      capturesList.appendChild(li);
    }
  }

  function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  async function checkHealth() {
    statusDot.className = "checking";
    statusLabel.textContent = "checking";

    const { apiUrl } = await chrome.storage.local.get({
      apiUrl: "http://localhost:8000",
    });

    try {
      const resp = await fetch(apiUrl + "/health", { signal: AbortSignal.timeout(5000) });
      if (resp.ok) {
        const data = await resp.json();
        if (data.status === "healthy") {
          statusDot.className = "online";
          statusLabel.textContent = "connected";
          return true;
        }
      }
      statusDot.className = "offline";
      statusLabel.textContent = "unhealthy";
      return false;
    } catch {
      statusDot.className = "offline";
      statusLabel.textContent = "offline";
      return false;
    }
  }

  captureNowBtn.addEventListener("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    try {
      await chrome.tabs.sendMessage(tab.id, { type: "MANUAL_CAPTURE" });
    } catch {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"],
      });
    }
    setTimeout(loadCaptures, 500);
  });

  clearBtn.addEventListener("click", async () => {
    await chrome.storage.local.set({ captures: [] });
    chrome.action.setBadgeText({ text: "" });
    loadCaptures();
  });

  document.addEventListener("DOMContentLoaded", async () => {
    await Promise.all([loadSettings(), loadCaptures(), checkHealth()]);
  });
})();
