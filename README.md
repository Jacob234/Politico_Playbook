# Politico Playbook Extraction Tool

A Python tool for extracting and processing Politico Playbook newsletters.

## Project Structure

```
politico_playbook/
├── src/               # Source code
├── data/             # Extracted newsletter data
├── logs/             # Log files
└── tests/            # Test files
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration (see `.env.example`)

## Usage

Run the main script:
```bash
python src/main.py
```

## Features

- Automated newsletter collection
- Data extraction and processing
- Error logging
- Test coverage

## Development

- Format code: `black src/`
- Lint code: `flake8 src/`
- Run tests: `pytest tests/` 