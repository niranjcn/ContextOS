(function () {
  "use strict";

  function extractPageData() {
    const selectors = [
      "article",
      '[role="main"]',
      "main",
      ".post-content",
      ".article-content",
      "#content",
      ".content",
      ".entry-content",
    ];

    let mainContent = "";
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim().length > 200) {
        mainContent = el.textContent.trim();
        break;
      }
    }

    if (!mainContent) {
      const body = document.body;
      if (body) {
        const clone = body.cloneNode(true);
        const tags = clone.querySelectorAll("script, style, nav, footer, header, aside");
        for (const t of tags) t.remove();
        mainContent = clone.innerText.trim();
      }
    }

    if (mainContent.length > 100000) {
      mainContent = mainContent.substring(0, 100000);
    }

    const meta = {};
    const metaTags = document.querySelectorAll("meta[name], meta[property]");
    for (const tag of metaTags) {
      const name = tag.getAttribute("name") || tag.getAttribute("property");
      const value = tag.getAttribute("content");
      if (name && value) meta[name] = value;
    }

    return {
      title: document.title,
      url: window.location.href,
      content: mainContent,
      metadata: meta,
    };
  }

  const data = extractPageData();
  chrome.runtime.sendMessage(
    { type: "PAGE_CAPTURED", data },
    () => undefined
  );

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "MANUAL_CAPTURE") {
      const fresh = extractPageData();
      chrome.runtime.sendMessage(
        { type: "MANUAL_PAGE_CAPTURED", data: fresh },
        () => undefined
      );
    }
  });
})();
