const DEFAULTS = {
  apiUrl: "http://localhost:8000",
  autoCapture: true,
  maxCaptures: 100,
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(DEFAULTS, (stored) => {
    chrome.storage.local.set(stored);
  });

  chrome.contextMenus.create({
    id: "capture-to-contextos",
    title: "Send to ContextOS",
    contexts: ["page"],
  });
});

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "PAGE_CAPTURED" || msg.type === "MANUAL_PAGE_CAPTURED") {
    handleCapture(msg.data, sender.tab?.id, msg.type === "MANUAL_PAGE_CAPTURED");
  }
});

async function handleCapture(data, tabId, isManual) {
  const { apiUrl, autoCapture, maxCaptures, captures } = await chrome.storage.local.get(
    DEFAULTS
  );

  const capture = {
    id: crypto.randomUUID(),
    title: data.title,
    url: data.url,
    capturedAt: new Date().toISOString(),
    sent: false,
    error: null,
  };

  const list = captures || [];
  list.unshift(capture);
  if (list.length > maxCaptures) list.length = maxCaptures;
  await chrome.storage.local.set({ captures: list });

  updateBadge(list);

  const shouldSend = autoCapture || isManual;
  if (!shouldSend) return;

  try {
    const docId = `web_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
    const resp = await fetch(`${apiUrl}/ingest/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: data.content,
        doc_id: docId,
        source: "browser_extension",
        metadata: {
          url: data.url,
          title: data.title,
          ...data.metadata,
        },
      }),
    });

    if (resp.ok) {
      capture.sent = true;
      capture.error = null;
    } else {
      const body = await resp.text();
      capture.error = `HTTP ${resp.status}: ${body.slice(0, 200)}`;
    }
  } catch (err) {
    capture.error = err.message;
  }

  await chrome.storage.local.set({ captures: list });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "capture-to-contextos" && tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: "MANUAL_CAPTURE" });
  }
});

function updateBadge(list) {
  const count = list.length;
  const text = count > 0 ? String(count) : "";
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color: "#4f46e5" });
}
