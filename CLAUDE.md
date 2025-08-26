# Politico Playbook Extraction Tool - Development Guide

## Project Overview

This is a proof-of-concept NLP data extraction tool for analyzing Politico Playbook newsletters to extract structured political intelligence data.

### Project Goals
1. **Automated Newsletter Collection**: Extract Politico Playbook emails from Gmail
2. **Text Processing**: Parse HTML newsletters into structured data
3. **Entity & Relationship Extraction**: Use NLP to identify:
   - Political figures and organizations
   - Personnel changes (appointments, departures)
   - Social/political relationships
   - Media appearances and events
4. **Data Storage**: Store extracted data in structured format (JSON/CSV/database)
5. **Visualization**: Eventually create network graphs showing political relationships

### Current Implementation Status - POST REORGANIZATION ✅
- ✅ **REORGANIZED**: Clean module structure with `politico_playbook/` as main package
- ✅ **SECURITY**: Environment variables implemented, no hardcoded credentials
- ✅ Email extraction script (`politico_playbook/src/extraction/email_client.py`)
- ✅ Basic file structure and organization
- ✅ Sample newsletter data collected (11 newsletters in `data/raw/` and `data/processed/`)
- ✅ JSON schema defined in `politico_playbook/src/models/schemas.py`
- ❌ NLP entity extraction not yet implemented
- ❌ Relationship extraction not yet implemented
- ❌ User interface not yet built

## NEW PROJECT STRUCTURE (COMPLETED)

### Final Structure
```
politico_playbook/
├── config/
│   ├── __init__.py
│   └── lexicon.json        # Moved from root
├── data/
│   ├── raw/               # HTML newsletters (migrated from src/data/newsletters/)
│   ├── processed/         # Extracted text (migrated from src/data/text/)
│   ├── structured/        # JSON outputs
│   └── playbook_metadata.csv
├── src/
│   ├── __init__.py
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── email_client.py    # Gmail connection (SECURED with env vars)
│   │   └── html_parser.py     # HTML to text conversion
│   ├── processing/
│   │   ├── __init__.py
│   │   └── [future NLP modules]
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # JSON schemas
│   └── utils/
│       ├── __init__.py
│       └── [future utilities]
├── tests/
│   └── __init__.py
├── main.py                # Main entry point
└── __init__.py           # Package root
```

### Root Level Files
```
├── .env                  # ✅ Created with Gmail credentials
├── .env.example         # ✅ Updated with Gmail template
├── .gitignore           # ✅ Already properly configured
├── CLAUDE.md           # This file
├── README.md           
├── requirements.txt    # ✅ Updated with NLP dependencies
├── playbook-poc-plan.md
└── to_do.md
```

## Key Development Commands

```bash
# Environment setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run email extraction
cd politico_playbook
python src/extraction/email_client.py

# Code quality
black politico_playbook/     # Format code
flake8 politico_playbook/    # Lint code
pytest tests/               # Run tests

# Import testing
python -c "from politico_playbook.src.extraction.email_client import main; print('Import successful')"
```

## Subagent Integration Points

### 1. Database Schema Architect (`database-schema-architect`)
**When to use**: Designing the SQLite database schema for storing extracted data
**Tasks**:
- Design normalized schema for entities, relationships, and events
- Create migration scripts for database updates
- Optimize queries for relationship traversal
- Implement indexing strategy for performance

### 2. Python Code Architect (`python-code-architect`)
**When to use**: Reviewing and refactoring the extraction/processing pipeline
**Tasks**:
- Review current code architecture and suggest improvements
- Design proper abstraction layers for the extraction pipeline
- Implement design patterns for extensibility
- Refactor duplicate code and improve modularity

### 3. Test Suite Engineer (`test-suite-engineer`)
**When to use**: Creating comprehensive test coverage
**Tasks**:
- Write unit tests for each extraction module
- Create integration tests for the full pipeline
- Develop fixtures for newsletter test data
- Implement continuous testing strategy

### 4. NLP Processor (`nlp-processor`)
**When to use**: Analyzing newsletter text and extracting entities/relationships
**Tasks**:
- Extract key personnel and organizations from text
- Identify relationship patterns in newsletters
- Perform similarity analysis between newsletters
- Extract keywords and themes from content

### 5. AI Service Integrator (`ai-service-integrator`)
**When to use**: If advanced text analysis beyond spaCy is needed
**Tasks**:
- Integrate Claude API for complex relationship extraction
- Implement prompt engineering for political context understanding
- Design fallback strategies for API failures
- Optimize API usage for cost efficiency

### 6. Documentation Auditor (`codebase-doc-auditor`)
**When to use**: After major refactoring to ensure documentation is current
**Tasks**:
- Update all docstrings and comments
- Ensure README accurately reflects new structure
- Document API endpoints and data formats
- Create user guides for the extraction pipeline

## Priority Tasks (Next Steps)

1. **HIGH**: Implement NLP entity extraction in `politico_playbook/src/processing/`
2. **HIGH**: Create relationship extraction patterns
3. **MEDIUM**: Build SQLite database storage system
4. **MEDIUM**: Complete text processing pipeline
5. **LOW**: Build visualization interface

## Updated Dependencies

```txt
# Core dependencies
requests==2.31.0
beautifulsoup4==4.12.2
python-dotenv==1.0.0
pandas==2.1.4
lxml==4.9.3

# NLP and text processing
spacy>=3.7.0
nltk>=3.8.0

# Database
sqlalchemy>=2.0.0

# Visualization and analysis
networkx>=3.2.0
matplotlib>=3.8.0
plotly>=5.17.0

# Web interface (for future development)
streamlit>=1.29.0
flask>=3.0.0

# Development tools
pytest==7.4.3
black==23.11.0
flake8==6.1.0
```

## Security Notes ✅ IMPLEMENTED

- ✅ Gmail credentials now stored in `.env` file (not committed to git)
- ✅ `.env.example` provides template for new developers
- ✅ `email_client.py` updated to use `os.getenv()` for credentials
- ✅ `.gitignore` properly configured to ignore sensitive files
- ✅ Removed hardcoded passwords from all source code

## Testing Strategy

1. **Unit Tests**: Test individual extraction functions
2. **Integration Tests**: Test full pipeline with sample data
3. **Regression Tests**: Ensure changes don't break existing functionality
4. **Performance Tests**: Monitor processing speed for large datasets

## Notes for Development

- Always use environment variables for sensitive data ✅
- Follow PEP 8 style guidelines
- Write tests for new functionality
- Document complex extraction patterns
- Use type hints for better code clarity
- Implement logging for debugging
- Consider rate limiting for email extraction
- Plan for incremental/resumable processing

## Migration Summary ✅ COMPLETED

**What was migrated**:
- `src/data/newsletters/` → `politico_playbook/data/raw/`
- `src/data/text/` → `politico_playbook/data/processed/`  
- `src/email_extractor.py` → `politico_playbook/src/extraction/email_client.py` (with env vars)
- `src/html_formatter.py` → `politico_playbook/src/extraction/html_parser.py`
- `src/main.py` → `politico_playbook/main.py`
- `lexicon.json` → `politico_playbook/config/lexicon.json`
- Created proper `__init__.py` files throughout package structure
- Updated `requirements.txt` with NLP dependencies

The project is now properly organized and ready for NLP implementation!