// Background script for AccessHelp extension
const API_BASE = 'http://localhost:8501';

chrome.runtime.onInstalled.addListener(() => {
    console.log('AccessHelp Extension Installed - Connected to Streamlit on port 8501');
    
    // Create context menu for selected text
    chrome.contextMenus.create({
        id: "accesshelp-read",
        title: "🔊 Read with AccessHelp",
        contexts: ["selection"]
    });
    
    chrome.contextMenus.create({
        id: "accesshelp-summarize",
        title: "📝 Summarize with AccessHelp",
        contexts: ["selection"]
    });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "accesshelp-read") {
        // Send to content script
        chrome.tabs.sendMessage(tab.id, {
            action: "read",
            text: info.selectionText
        });
    } else if (info.menuItemId === "accesshelp-summarize") {
        chrome.tabs.sendMessage(tab.id, {
            action: "summarize",
            text: info.selectionText
        });
    }
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkAPI") {
        // Check if Streamlit is running
        fetch(`${API_BASE}`)
            .then(() => sendResponse({status: "online"}))
            .catch(() => sendResponse({status: "offline"}));
        return true; // Keep message channel open
    }
});