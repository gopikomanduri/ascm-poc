// This extension intentionally sends only the hostname, never the full URL or tab title.
const hostName = "com.ascm.activity";
const seenByTab = new Map();

function hostnameFromUrl(url) {
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
    if (!host || host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return null;
    return host;
  } catch (_) {
    return null;
  }
}

function recordTab(tabId, url) {
  const domain = hostnameFromUrl(url || "");
  if (!domain || seenByTab.get(tabId) === domain) return;
  seenByTab.set(tabId, domain);
  chrome.runtime.sendNativeMessage(hostName, {
    type: "browser_domain",
    domain: domain,
    timestamp: new Date().toISOString()
  }, () => {
    // Native host unavailable? Keep browser usable; don't persist the URL or error payload.
    void chrome.runtime.lastError;
  });
}

chrome.tabs.onActivated.addListener(({tabId}) => {
  chrome.tabs.get(tabId, tab => {
    if (tab && tab.url) recordTab(tabId, tab.url);
  });
});
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url && tab && tab.active) recordTab(tabId, changeInfo.url);
});
chrome.tabs.onRemoved.addListener(tabId => seenByTab.delete(tabId));
