# Teni - Personal AI System for macOS

Phase 1: Local AI Control Layer

## Overview

Teni is a system-level AI companion for macOS that accepts text commands and executes real system actions using natural language processing.

## Architecture

- **Layer 1**: Text CLI Interface
- **Layer 2**: LLM Integration (gpt-oss:120b-cloud via Ollama Cloud API)
- **Layer 3**: Intent Validation & Security
- **Layer 4**: macOS Execution Engine

## Features

- Natural language command processing
- Structured JSON intent generation
- Safe command validation
- macOS system control via AppleScript
- File system operations
- Web browsing automation
- Command logging and memory
- Security-first design

## Installation

1. Clone or navigate to the Teni directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure `.env` file contains your Ollama API key

## Usage

Run the system:
```bash
python3 main.py
```

Example commands:
- `open safari and search ib chemistry acids`
- `create folder named Projects on Desktop`
- `split screen safari and notes`
- `list files in Downloads`
- `write email draft to team about meeting`

## Security Features

- Whitelisted actions only
- Shell command validation
- File path traversal protection
- Confirmation for dangerous operations
- No sudo or password access

## Project Structure

```
teni/
├── main.py              # CLI interface
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── .env                 # API keys
├── llm/                 # LLM integration
├── intent/              # Intent processing
├── execution/           # macOS control
├── memory/              # Command history
├── logs/                # System logs
└── utils/               # Utilities
```

## Allowed Actions (Phase 1)

- open_app, close_app
- open_website, search_web
- create_folder, rename_file, move_file, delete_file, list_files
- split_screen
- write_email_draft
- run_shell_safe

## Configuration

Edit `config.py` to modify:
- API endpoints
- Allowed actions
- Safe shell commands
- File paths
