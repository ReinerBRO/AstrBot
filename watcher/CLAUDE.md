# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Watcher（日常工作助手）** is an intelligent work activity tracking system that monitors screen activity during configured time windows, analyzes user behavior using VL (Vision-Language) models and event signals, and generates visual "growth tree" reports with automatic activity classification.

### Core Capabilities
- **Dual-Signal Analysis**: Screenshot analysis (VL model) + user behavior tracking (clicks, window switches)
- **Intelligent Fusion**: Weighted fusion of visual and behavioral signals (VL 70% + Event 30%)
- **Smart Triggering**: Cost-optimized analysis based on screen changes and user activity
- **Multi-Tree Reports**: Daily activity organized into visual tree structures with timeline
- **Hybrid Classification**: Rule-based (80%, free) + LLM-based (20%, paid) for optimal accuracy and cost

### Recent Major Update (2026-02-11)
✅ **Event Fusion System** - Integrated click/window event tracking with screenshot analysis
- Event classification accuracy: 70% → 85-90%
- Final classification accuracy improvement: 5-10%
- 24 automated tests (unit + integration)

## Architecture

### Module Structure

**`watcher/`** - Backend monitoring engine
- `runner.py`: Main `Watcher` class orchestrating the monitoring loop
- `capture.py`: Screenshot capture (mss with PIL fallback)
- `diff.py`: aHash + Hamming distance for change detection
- `api_client.py`: `VLClient` for VL/text model API calls
- `scheduler.py`: Time window logic
- `reporter.py`: Markdown report + log file writing
- `config.py`: Environment-based configuration
- `trigger.py`: `TriggerDetector` for intelligent analysis triggering

**`watcher/event_source/`** - Event collection system (NEW)
- `click_listener.py`: Mouse click monitoring using `pynput`
- `window_resolver.py`: Active window info (app name, title)
- `event_buffer.py`: 5-minute sliding window aggregation
- `event_logger.py`: JSONL event logging
- `models.py`: Data models (`ClickEvent`, `AggregatedFeatures`)

**`watcher/signal_fusion/`** - Classification and fusion (NEW)
- `event_classifier.py`: Rule-based event classifier (keyword matching)
- `llm_event_classifier.py`: LLM-based deep semantic classifier
- `hybrid_classifier.py`: Intelligent rule/LLM selection
- `fusion_engine.py`: VL + Event weighted fusion with conflict resolution

**`app/`** - Web application layer
- `service.py`: `WatcherService` orchestrates watcher lifecycle, tree CRUD
- `web.py`: Flask routes (`/api/status`, `/api/start`, `/api/tree`, etc.)
- `main.py`: Flask app factory
- `web_static/`: Frontend (vanilla JS, no build step)

**`reports/`** - Generated daily reports
- `YYYY-MM-DD.md`: Markdown entries with time, category, summary, tree_id
- `YYYY-MM-DD.trees.json`: Tree metadata (id, name, created_at, deleted)

**`logs/`** - Runtime logs
- `YYYY-MM-DD.log`: Application logs
- `click-events-YYYY-MM-DD.jsonl`: Event logs (NEW)

### Data Flow

```
┌─────────────┐     ┌──────────────┐
│  Screenshot │     │ Click Events │
│   Capture   │     │  (pynput)    │
└──────┬──────┘     └──────┬───────┘
       │                   │
       ▼                   ▼
  ┌─────────┐      ┌──────────────┐
  │  aHash  │      │Event Buffer  │
  │  Diff   │      │(5min window) │
  └────┬────┘      └──────┬───────┘
       │                  │
       ▼                  ▼
  ┌─────────────┐  ┌─────────────┐
  │   Trigger   │◄─┤   Trigger   │
  │  Detector   │  │  Detector   │
  └──────┬──────┘  └─────────────┘
         │
         ▼ (if triggered)
  ┌─────────────┐  ┌──────────────┐
  │ VL Analysis │  │Event Classify│
  │  (qwen-vl)  │  │(Rule or LLM) │
  └──────┬──────┘  └──────┬───────┘
         │                │
         └────────┬───────┘
                  ▼
          ┌──────────────┐
          │Fusion Engine │
          │ (0.7 + 0.3)  │
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │Final Category│
          │   & Report   │
          └──────────────┘
```

### Key Algorithms

**1. Trigger Detection**
- Screen diff ≥ threshold → trigger
- Idle time ≥ max interval → trigger
- Event signal (clicks ≥ 6 or app switch) + min interval elapsed → trigger

**2. Event Classification**
- Rule-based: Keyword matching (fast, free, 70% accuracy)
- LLM-based: Deep semantic analysis (slow, paid, 85-90% accuracy)
- Hybrid: Use LLM only when rule confidence < threshold

**3. Signal Fusion**
- VL result (0.7 weight) + Event result (0.3 weight)
- Conflict resolution: Compare confidence, check consistency, conservative fallback
- Last category context for temporal consistency

**4. Tree Auto-Grouping**
- Entries within 20min of explicit tree → inherit tree
- Otherwise, create new auto-tree if gap > 45min

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Run Application
```bash
# Recommended: one-command start (loads .env, starts Flask on 127.0.0.1:8000)
python run.py

# Alternative: run web module directly
python -m app

# Run watcher loop only (no web UI)
python -m watcher
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=watcher --cov=app --cov-report=term-missing

# Syntax check
python -m compileall app watcher

# Frontend syntax check
node --check app/web_static/app.js
```

## Configuration

All config via `.env` file (never commit this file):

### Required
```bash
VL_API_URL=https://api.example.com/v1    # VL model endpoint
VL_API_KEY=sk-...                         # API key
```

### Model Selection
```bash
VL_MODEL=qwen-vl-max                      # Screenshot analysis
EVENT_SUMMARY_MODEL=qwen3-max             # Event summarization (unused in current version)
FUSION_SUMMARY_MODEL=qwen3-max            # Fusion summarization (unused in current version)
```

### Throttling & Cost Control
```bash
WATCH_INTERVAL_S=30                       # Polling interval
MIN_SEND_INTERVAL_S=300                   # Minimum time between API calls
MAX_IDLE_SEND_INTERVAL_S=900              # Force send if idle
HASH_DIFF_THRESHOLD=8                     # Hamming distance threshold
```

### Event Source (NEW)
```bash
ENABLE_EVENT_SOURCE=true                  # Enable click/window tracking
EVENT_PRIVACY_MASK=true                   # Mask window titles
EVENT_BUFFER_WINDOW_S=300                 # Event aggregation window
EVENT_TRIGGER_MIN_CLICKS=6                # Min clicks to trigger
EVENT_SWITCH_TRIGGER=true                 # Window switch triggers
EVENT_LOG_DIR=logs                        # Event log directory
```

### Fusion Engine (NEW)
```bash
FUSION_VL_WEIGHT=0.7                      # VL signal weight
FUSION_EVENT_WEIGHT=0.3                   # Event signal weight
FUSION_CONFIDENCE_THRESHOLD=0.5           # Confidence threshold
```

### LLM Event Classifier (NEW, Optional)
```bash
USE_LLM_EVENT_CLASSIFIER=false            # Enable LLM classifier
LLM_EVENT_MODEL=gpt-4o-mini               # LLM model for events
LLM_EVENT_THRESHOLD=0.6                   # Rule confidence threshold
LLM_EVENT_ALWAYS=false                    # Always use LLM
LLM_EVENT_TIMEOUT_S=10.0                  # API timeout
```

### Categories
```bash
TASK_CATEGORIES=写代码,研究,娱乐           # Comma-separated (max 8)
```

## API Endpoints

### Core
- `GET /api/status` - System status (includes event source status)
- `POST /api/start` - Start monitoring
- `POST /api/stop` - Stop monitoring
- `POST /api/manual` - Manual snapshot
- `POST /api/preferences` - Update preferences

### Tree Management
- `GET /api/tree?date=...&tree_id=...` - Get tree data
- `POST /api/tree/create` - Create new tree
- `POST /api/tree/delete` - Delete tree

### Event Source (NEW)
- `GET /api/event-source/status` - Event source status
- `GET /api/event-source/summary` - Event summary (clicks, apps, etc.)

### Logs
- `GET /api/logs?lines=...&date=...` - Get logs

## Important Implementation Notes

### Event Source Platform Support
- **macOS**: Uses `pynput` + `Quartz` (requires Accessibility permission)
- **Linux**: Uses `pynput` + `python-xlib`
- **Windows**: Not implemented (gracefully disabled)

### Accessibility Permission (macOS)
The app requires Accessibility permission to monitor clicks and windows:
1. System Preferences → Security & Privacy → Privacy → Accessibility
2. Add Terminal or your Python interpreter
3. Check `check_accessibility_permission()` in logs

### Classification Strategy
1. **VL Analysis**: Always runs when triggered, provides summary + optional category
2. **Event Classification**: Only runs if events exist (clicks > 0)
   - Rule-based: Fast keyword matching
   - LLM-based: Deep analysis (optional, controlled by `USE_LLM_EVENT_CLASSIFIER`)
3. **Fusion**: Combines VL + Event results with weighted average and conflict resolution

### Cost Optimization
- **Screen diff throttling**: Only analyze when screen changes significantly
- **Event-based triggering**: Analyze when user is active (clicks/switches)
- **Hybrid classification**: 80% rule-based (free), 20% LLM (paid)
- **Minimum intervals**: Prevent excessive API calls

### Frontend State Management
- `Start` button locks time/frequency/category inputs
- `Stop` button unlocks inputs
- Tree visualization uses manual SVG rendering (no external libs)
- Date picker shows only dates with data

## Common Pitfalls

1. **Missing VL_API_URL**: App starts but watcher won't run. Check `/api/status` for `api_ready: false`

2. **Accessibility Permission**: On macOS, event source won't work without permission. Check logs for "permission=False"

3. **High API costs**: Verify throttling params are set appropriately. Monitor logs for "sent" frequency.

4. **Event source fails silently**: Check logs for "event-source enabled=False" or "listener=False"

5. **Classification mismatch**: VL model must return category from `TASK_CATEGORIES` list. Fallback uses keyword classification.

6. **Fusion not working**: Requires `ENABLE_EVENT_SOURCE=true` and valid event data. Check logs for "event-classifier" entries.

7. **LLM classifier timeout**: If `USE_LLM_EVENT_CLASSIFIER=true`, ensure `LLM_EVENT_TIMEOUT_S` is sufficient for your API.

## Testing Strategy

### Unit Tests
- Event buffer aggregation (`tests/test_event_buffer.py`)
- Event classification (`tests/test_event_classifier.py`)
- LLM classifier (`tests/test_llm_event_classifier.py`)
- Fusion engine (`tests/test_fusion_engine.py`)
- Trigger detector (`tests/test_trigger.py`)

### Integration Tests
- End-to-end classification flow
- API endpoint responses
- Event source integration

### Coverage Target
- Current: 86% for LLM classifier, 70%+ overall
- Goal: 80%+ for all modules

## File Locations

- Reports: `reports/YYYY-MM-DD.md` and `reports/YYYY-MM-DD.trees.json`
- Logs: `logs/YYYY-MM-DD.log`
- Event logs: `logs/click-events-YYYY-MM-DD.jsonl` (NEW)
- Config: `.env` (root directory, gitignored)
- Frontend: `app/web_static/` (served at `/` by Flask)

## Next Steps

1. ~~Event fusion system~~ ✅ Completed (2026-02-11)
2. Daily report independent view (not yet implemented)
3. Continue optimizing classification accuracy (LLM prompts, rule library)
4. Enhance robustness (API retry/backoff/fallback)
5. Add E2E tests and performance tests
