// Clicking the toolbar icon opens the game in a new tab. No extra permissions needed.
function openGame() {
  chrome.tabs.create({ url: chrome.runtime.getURL("game.html") });
}

chrome.action.onClicked.addListener(openGame);

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") openGame();
});
