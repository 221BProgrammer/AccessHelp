// Content script for AccessHelp - Connects to Streamlit on port 8501
console.log('AccessHelp Extension Loaded - Looking for Streamlit on port 8501');

const API_BASE = 'http://localhost:8501';
let floatingButton = null;

// Function to send text to Streamlit
async function sendToStreamlit(text, action) {
    try {
        // Use the Streamlit query parameter method
        const currentUrl = new URL(window.location.href);
        const command = {
            action: action,
            text: text.substring(0, 500), // Limit text length
            timestamp: new Date().toISOString(),
            source: 'browser_extension'
        };
        
        // Store in localStorage for Streamlit to read
        localStorage.setItem('accesshelp_command', JSON.stringify(command));
        
        // Open AccessHelp in new tab with the command
        const accesshelpUrl = `${API_BASE}?action=${action}&text=${encodeURIComponent(text.substring(0, 500))}`;
        
        // Check if AccessHelp tab already exists
        const tabs = await chrome.tabs.query({url: `${API_BASE}*`});
        if (tabs.length > 0) {
            // Focus existing tab and reload with command
            await chrome.tabs.update(tabs[0].id, {active: true, url: accesshelpUrl});
        } else {
            // Open new tab
            await chrome.tabs.create({url: accesshelpUrl});
        }
        
        console.log(`Sent to AccessHelp: ${action} - ${text.substring(0, 50)}...`);
        return true;
    } catch (error) {
        console.error('AccessHelp not running:', error);
        return false;
    }
}

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "read") {
        sendToStreamlit(request.text, "speak");
    } else if (request.action === "summarize") {
        sendToStreamlit(request.text, "summarize");
    }
});

// Create floating button
function createFloatingButton() {
    if (floatingButton) return;
    
    floatingButton = document.createElement('div');
    floatingButton.id = 'accesshelp-button';
    floatingButton.innerHTML = '🔊';
    floatingButton.title = 'Read with AccessHelp';
    floatingButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 9999;
        font-size: 24px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        font-family: Arial, sans-serif;
    `;
    
    floatingButton.onmouseenter = () => {
        floatingButton.style.transform = 'scale(1.1)';
        floatingButton.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
    };
    
    floatingButton.onmouseleave = () => {
        floatingButton.style.transform = 'scale(1)';
        floatingButton.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    };
    
    floatingButton.onclick = () => {
        const selectedText = window.getSelection().toString();
        if (selectedText && selectedText.length > 0 && selectedText.length < 500) {
            sendToStreamlit(selectedText, "speak");
            // Visual feedback
            floatingButton.style.transform = 'scale(0.95)';
            setTimeout(() => {
                floatingButton.style.transform = 'scale(1)';
            }, 200);
        } else {
            // No text selected, show tooltip
            const tooltip = document.createElement('div');
            tooltip.textContent = 'Select some text first!';
            tooltip.style.cssText = `
                position: fixed;
                bottom: 80px;
                right: 20px;
                background: #333;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                z-index: 10000;
                font-family: Arial, sans-serif;
            `;
            document.body.appendChild(tooltip);
            setTimeout(() => tooltip.remove(), 2000);
        }
    };
    
    document.body.appendChild(floatingButton);
}

// Check if user wants floating button
chrome.storage.local.get(['enableFloatingButton'], (result) => {
    if (result.enableFloatingButton !== false) {
        createFloatingButton();
    }
});

// Add keyboard shortcut hint
document.addEventListener('keydown', (e) => {
    // Alt + R to read selected text
    if (e.altKey && e.key === 'r') {
        const selectedText = window.getSelection().toString();
        if (selectedText) {
            sendToStreamlit(selectedText, "speak");
        }
    }
});