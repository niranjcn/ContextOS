# ContextOS Browser Extension

Captures web pages into your local ContextOS knowledge base.

## How it works

1. **Auto-capture** — When enabled, every page you visit is automatically extracted and sent to ContextOS
2. **Manual capture** — Right-click any page and select "Send to ContextOS", or click the extension icon and press "Capture now"
3. **All local** — Data is sent only to your local ContextOS API at `http://localhost:8000`

## Installation (unpacked)

1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked" and select the `browser-extension/` directory
4. The extension icon appears in the toolbar

## Usage

- The extension icon badge shows the number of captured pages
- Click the icon to open the popup
- Toggle auto-capture on/off
- View recently captured pages and their sync status
- Click "Capture now" to manually capture the current tab
- Right-click any page > "Send to ContextOS"

## Requirements

- ContextOS API running on `http://localhost:8000` (from Docker or direct Python)
- Chrome/Chromium 88+ (Manifest V3)
