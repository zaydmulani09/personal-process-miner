# Personal Process Miner

[![CI](https://github.com/zaydmulani09/personal-process-miner/actions/workflows/ci.yml/badge.svg)](https://github.com/zaydmulani09/personal-process-miner/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)

> A privacy-first desktop app that learns your repetitive computer workflows and turns them into one-click automations — all locally, nothing sent to the cloud.

## What It Does

Personal Process Miner runs silently in the background, watching which apps you switch between and when. It detects sequences you repeat — "open Slack, copy a number, paste into Excel, close Slack" — and tells you exactly how many hours those repetitive habits are costing you each week. When it finds a pattern worth automating, it generates a ready-to-run PyAutoGUI or Playwright script. One click and it runs. That's the whole loop: **capture → detect → automate**.

The first time you see "you wasted 4 hours this week switching between these three apps," you'll want to fix it. Process Miner shows you how.

## Demo

![Demo](docs/demo.gif)
<!-- Add a screen recording here -->

## Features

- **Local-first** — all data stays on your machine, no accounts, no sync, no telemetry
- **Automatic sequence detection** — sliding-window fingerprinting finds repeated app-switch patterns without any manual tagging
- **Script generation** — produces runnable PyAutoGUI macros and Playwright browser scripts
- **Universal AI Vision** — choose from Claude, OpenAI (GPT-4o), Groq, Gemini, or Grok for smart screen-aware automations (opt-in, key stored locally)
- **Optional AI improvement** — connect Ollama (local) or Claude API for smart script refactoring (opt-in via env vars)
- **Privacy controls** — blocklist specific apps, purge all data anytime, control exactly what gets recorded
- **Onboarding wizard** — first-run flow explains what's recorded, asks for permissions, runs a 60-second demo
- **Shareable insights card** — screenshot-ready weekly summary of time saved
- **Works on Windows and macOS**

## Quick Start

### Download (recommended)

Grab the latest installer from [GitHub Releases](https://github.com/zaydmulani09/personal-process-miner/releases).

- **Windows**: `.msi` installer or `.exe` (NSIS)
- **macOS**: `.dmg`

### Build from Source

Prerequisites: [Rust](https://rustup.rs), [Node 20+](https://nodejs.org), [Python 3.11+](https://python.org), VS Build Tools 2022 (Windows)

```bash
git clone https://github.com/zaydmulani09/personal-process-miner
cd personal-process-miner
py -m pip install -r sidecar/requirements.txt
py -m playwright install chromium
npm install
npm run tauri build
```

The built app is at `src-tauri/target/release/`.

## How It Works

1. **Capture** — pynput records keyboard events, mouse clicks, and active window changes. `app_name` is resolved via `QueryFullProcessImageNameW` on Windows. Events are written to a local SQLite DB.

2. **Segment** — sessions are carved out of the event stream using idle-gap detection (5-minute default), midnight boundaries, and max-length limits. Each session gets a `dominant_app` label.

3. **Fingerprint** — a sliding window extracts subsequences of app-switch events. Candidate patterns are compared with edit distance to deduplicate fuzzy variants. Survivors are stored as workflows with frequency and duration stats.

4. **Rank & Automate** — workflows are scored by `frequency × avg_duration`. The ranker surfaces the highest-value patterns. From any workflow you can record a PyAutoGUI macro, generate a Playwright script, or let the LLM explainer suggest improvements.

## Optional: AI Improvement

Set environment variables before launching the app:

```bash
# Use local Ollama (default model: mistral)
PPM_LLM_BACKEND=ollama
PPM_OLLAMA_URL=http://localhost:11434   # optional, this is the default

# Use Claude API
PPM_LLM_BACKEND=claude
PPM_CLAUDE_API_KEY=sk-ant-...
```

With a backend configured, each automation card gains an "✨ Improve" button that sends the script to the LLM for explanation and refactoring. No backend = app works exactly as before.

## Privacy

**What gets recorded:** which apps are active, when you switch apps, mouse clicks, window titles.

**What is never recorded:** what you type (keystrokes are masked as `[key]` by default), passwords, screen contents, activity from any app on your blocklist.

**To purge:** open Settings → Danger Zone → type `DELETE` → Purge All Data. All events, sessions, workflows, and automations are deleted immediately from the local DB. Nothing to call home about.

All data is stored locally in a SQLite database on your device — no telemetry, no analytics, no cloud sync. **AI Vision is fully opt-in**: screenshots are only sent to your chosen AI provider when you explicitly trigger a vision action. API keys are stored locally and never transmitted to the app developers.

See [PRIVACY.md](PRIVACY.md) for the full privacy policy.

## Security

- **HTTP server binds to localhost only** (`127.0.0.1:7834`) — no external network exposure
- **No data leaves your device** except optional AI Vision API calls you explicitly configure
- **API keys stored locally** in SQLite — never sent to app developers
- **Input validation** on all IPC handlers — type checks, size limits, list caps
- **Rate limiting** on the local HTTP server — 60 requests/minute per IP
- All SQL queries use parameterized statements — no string interpolation with user input

## Development

```bash
# Run in dev mode (opens a browser window at localhost:1420)
npm run tauri dev

# Run the Python sidecar standalone
py sidecar/main.py

# Run test suites
py sidecar/test_db.py
py sidecar/test_segmenter.py
py sidecar/test_fingerprinter.py
py sidecar/test_ranker.py
py sidecar/test_llm_explainer.py
py sidecar/test_scheduler.py

# These require a running sidecar or OS GUI (run locally, not CI):
# py sidecar/test_ipc.py      (needs: py sidecar/seed.py first)
# py sidecar/test_capture.py
# py sidecar/test_macro_recorder.py
# py sidecar/test_playwright_gen.py
```

## License

MIT © 2026 zaydmulani09
