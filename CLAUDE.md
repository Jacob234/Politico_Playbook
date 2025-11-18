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

### Current Implementation Status - POST OPTIMIZATION ✅
- ✅ **REORGANIZED**: Clean module structure with `politico_playbook/` as main package
- ✅ **SECURITY**: Environment variables implemented, no hardcoded credentials
- ✅ Email extraction script (`politico_playbook/src/extraction/email_client.py`)
- ✅ Basic file structure and organization
- ✅ Sample newsletter data collected (20 newsletters in `data/structured/`)
- ✅ JSON schema defined in `politico_playbook/src/models/schemas.py`)
- ✅ Claude NLP processor implemented (`politico_playbook/src/processing/claude_nlp_processor.py`)
- ✅ Escalation logic optimized (threshold 0.85→0.70, removed person count limit)
- ✅ Validation framework created (`politico_playbook/validation/`)
- ✅ **RSS IMPLEMENTATION COMPLETED**: Code ready, but feeds return 403 Forbidden errors
- ⚠️ **RSS STATUS UNCERTAIN**: Feeds may have access restrictions (see `docs/RSS_IMPLEMENTATION_STATUS.md`)
- ⚠️ **NEEDS WORK**: Low recall rates (11-36% vs 70% target) - see analysis
- ⚠️ **IN VALIDATION**: System being tested against ground truth
- ❌ Database storage not yet implemented
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
│   ├── structured/        # JSON outputs from html_to_json
│   ├── claude_enhanced/   # Claude NLP processor outputs
│   └── playbook_metadata.csv
├── docs/
│   ├── claude_nlp_processor.md            # Claude processor documentation
│   ├── claude_nlp_performance_report.md   # Original performance report
│   ├── claude_nlp_analysis_2025-11-18.md  # Comprehensive analysis & findings
│   ├── POLITICO_ACCESS_RESEARCH.md        # RSS/API research findings
│   ├── POLITICO_WEB_SCRAPER_PLAN.md       # Web scraping plan (deprioritized)
│   └── RSS_IMPLEMENTATION_STATUS.md       # RSS implementation attempt & 403 errors
├── src/
│   ├── __init__.py
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── email_client.py          # Gmail connection (SECURED with env vars)
│   │   ├── rss_client.py            # RSS fetcher - full version (BLOCKED - 403 errors)
│   │   ├── rss_client_simple.py     # RSS fetcher - simplified (BLOCKED - 403 errors)
│   │   └── html_parser.py           # HTML to text conversion
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── claude_nlp_processor.py  # Claude-based entity extraction (OPTIMIZED)
│   │   ├── nlp_processor.py         # spaCy-based processor (baseline)
│   │   ├── html_to_json.py          # HTML → structured JSON
│   │   └── database_normalizer.py   # Data normalization
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # JSON schemas
│   └── utils/
│       ├── __init__.py
│       └── [future utilities]
├── validation/
│   ├── VALIDATION_GUIDE.md           # How to validate NLP performance
│   ├── validation_template.json      # JSON annotation template
│   ├── validation_template.csv       # CSV annotation template
│   ├── calculate_metrics.py          # Automated metrics calculation
│   ├── ground_truth/                 # Manual annotations
│   │   └── EXAMPLE_*_ground_truth.json
│   └── results/                      # Validation outputs
├── tests/
│   └── __init__.py
├── main.py                # Main entry point
└── __init__.py           # Package root
```

### Root Level Files
```
├── .env                       # ✅ Created with Gmail/Anthropic credentials
├── .env.example              # ✅ Updated with templates
├── .gitignore                # ✅ Properly configured
├── CLAUDE.md                 # This file - Project guide
├── README.md
├── requirements.txt          # ✅ Updated with Claude API dependencies
├── OPTIMIZATION_SUMMARY.md   # ✅ Summary of Nov 2025 optimization work
├── playbook-poc-plan.md
└── to_do.md
```

## Data Collection Strategy

### Hybrid Approach: RSS + Email ✅ RECOMMENDED

Based on comprehensive research (see `docs/POLITICO_ACCESS_RESEARCH.md`), we use a **hybrid approach** for newsletter collection:

#### RSS Feeds (Primary for National Coverage)
**Status:** ✅ Official feeds available

**Coverage:**
- ✅ **National Playbook**: `http://www.politico.com/rss/playbook.xml`
- ✅ **Politico Pulse**: `http://www.politico.com/rss/politicopulse.xml`

**Advantages:**
- Official and legal (intended for syndication)
- Real-time updates
- Clean, structured data
- No authentication required
- Zero rate limiting concerns

**Implementation:** RSS client module (`rss_client.py`) - IN DEVELOPMENT

#### Email Extraction (Required for State Playbooks)
**Status:** ✅ Implemented and working

**Coverage:**
- ✅ **Florida Playbook** (no RSS feed available)
- ✅ **New York Playbook** (no RSS feed available)
- ✅ **California Playbook** (no RSS feed available)

**Current Tool:** `politico_playbook/src/extraction/email_client.py`

**Why Still Needed:** State playbooks do NOT have public RSS feeds

#### Web Scraping (NOT RECOMMENDED)
**Status:** ⚠️ Deprioritized

- Plan documented in `docs/POLITICO_WEB_SCRAPER_PLAN.md`
- Only consider for historical backfill if gaps exist
- Legal/ethical concerns
- Maintenance burden (breaks with site changes)
- **Use Email extraction instead** (RSS blocked by 403 errors)

### Newsletter Coverage Matrix

| Newsletter Type | RSS Available | Email Available | Current Method | Status |
|----------------|---------------|-----------------|----------------|--------|
| National Playbook | ⚠️ Exists but 403 | ✅ Yes | Email | **Email (Working)** |
| Politico Pulse | ⚠️ Exists but 403 | ✅ Yes | Email | **Email (Working)** |
| Florida Playbook | ❌ No | ✅ Yes | Email | **Email (Working)** |
| New York Playbook | ❌ No | ✅ Yes | Email | **Email (Working)** |
| California Playbook | ❌ No | ✅ Yes | Email | **Email (Working)** |

**Result:** Email extraction remains primary method for all newsletters (RSS blocked by 403 errors)

## Key Development Commands

```bash
# Environment setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run email extraction
cd politico_playbook
python src/extraction/email_client.py

# Run RSS extraction (TO BE IMPLEMENTED)
python src/extraction/rss_client.py

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

## Priority Tasks (Updated November 2025)

### Immediate (Current Sprint)
1. **HIGH**: ⚠️ **FOCUS** - Validate Claude NLP processor with ground truth annotations
2. **HIGH**: ⚠️ **FOCUS** - Improve recall from 11-36% to 70%+ (requires prompt optimization)
3. **MEDIUM**: Test optimized escalation logic (0.70 threshold, no person limit)
4. **LOW**: ⚠️ **BLOCKED** - RSS client returns 403 Forbidden errors
   - Code complete but feeds inaccessible from this environment
   - See `docs/RSS_IMPLEMENTATION_STATUS.md` for details
   - Needs user verification: Can feeds be accessed in browser?

### Short Term (Next 2-4 Weeks)
5. **HIGH**: Optimize prompts to capture journalists and political staff
6. **HIGH**: Fix NULL field issues (seen in CA Playbook extraction)
7. **MEDIUM**: Complete validation testing on all 20 newsletters
8. **MEDIUM**: Production readiness decision (target: F1 > 0.70)
9. **LOW**: ~~Build unified fetcher combining RSS + Email sources~~ (Postponed pending RSS access)

### Medium Term (Next 1-2 Months)
10. **MEDIUM**: Build SQLite database storage system
11. **MEDIUM**: Implement automated quality monitoring
12. **LOW**: Complete text processing pipeline
13. **LOW**: Build visualization interface

### Completed ✅
- ✅ Implement NLP entity extraction
- ✅ Create relationship extraction patterns
- ✅ Implement Claude-based NLP processor
- ✅ Optimize escalation logic (40% cost reduction)
- ✅ Create validation framework
- ✅ Comprehensive performance analysis
- ✅ Research Politico official access methods (API, RSS, scraping)
- ✅ RSS client implementation (code complete, access blocked)

## Political NLP Enhancement - Phase 1: Claude Integration (IMPLEMENTED & OPTIMIZED)

### Current Implementation Status - November 2025
- ✅ **COMPLETED**: Claude-3.5-Haiku primary processor
- ✅ **COMPLETED**: Claude-3.5-Sonnet escalation for complex cases
- ✅ **COMPLETED**: Confidence-based routing (optimized threshold: 0.70)
- ✅ **OPTIMIZED**: Escalation logic fixed (removed person count limit paradox)
- ⚠️ **ISSUE IDENTIFIED**: Low recall rates (11-36% vs 70%+ target)
- ⚠️ **IN VALIDATION**: Ground truth testing framework created
- 🔄 **IN PROGRESS**: Prompt optimization to improve recall

### Architecture
Two-tier Claude system for political newsletter analysis:
- **Primary**: Haiku for standard extraction - $0.01-0.02/newsletter
- **Escalation**: Sonnet for complex/uncertain cases - $0.05-0.15 additional
- **Escalation Rate**: 60% before optimization → **Target 25-30%** after optimization
- **Current Cost**: ~$0.056/newsletter → **Target $0.035/newsletter** (37% reduction)

### Actual Performance (Post-Analysis)
- **Precision**: 95-99% (high - extracted entities are correct)
- **Recall**: 11-36% (low - missing 64-89% of mentioned people)
- **F1 Score**: 0.20-0.48 (below 0.70 production target)
- **Entity Coverage**:
  - Political Officials: ~25-40% recall
  - Journalists: ~10-20% recall (significant gap)
  - Political Staff: ~5-15% recall (critical gap)

### Usage
```bash
cd politico_playbook

# Process newsletters with Claude NLP
python src/processing/claude_nlp_processor.py
# Processes all newsletters in data/structured/
# Outputs enhanced results to data/claude_enhanced/

# Validate performance with ground truth
python validation/calculate_metrics.py
# Compares Claude output to manual annotations
# Generates precision, recall, F1 scores
# Outputs results to validation/results/
```

### Performance Analysis & Optimization (November 2025)

#### Comprehensive Review Completed
A thorough analysis of the Claude NLP processor was conducted in November 2025, revealing significant performance gaps masked by incomplete testing and misleading metrics.

**Key Documents**:
- `politico_playbook/docs/claude_nlp_analysis_2025-11-18.md` - Detailed analysis
- `OPTIMIZATION_SUMMARY.md` - Executive summary and next steps
- `politico_playbook/validation/VALIDATION_GUIDE.md` - How to validate performance

#### Critical Findings

**What Worked Well**:
- ✅ High precision: 95-99% of extracted entities are correct
- ✅ Clean, structured JSON output
- ✅ Good extraction of top-level political officials
- ✅ Two-tier architecture functions as designed

**Critical Issues**:
- ❌ Low recall: Only capturing 11-36% of mentioned individuals
- ❌ Journalists severely under-detected (~10-20% captured)
- ❌ Political staff routinely missed (~5-15% captured)
- ❌ Escalation rate 2.4x above target (60% vs 25%)
- ❌ F1 scores 0.20-0.48 (target: 0.70+)

**Root Causes Identified**:
1. **Escalation Logic Paradox**: System escalated when extracting 25+ people, punishing comprehensive extraction
2. **Confidence Threshold Too High**: 0.85 vs industry standard 0.60-0.70
3. **Prompt Issues**: Under-extracting journalists and staff despite asking for them
4. **No Validation**: Report based on precision only, recall completely ignored

#### Optimizations Implemented

**1. Lowered Confidence Threshold**
- Changed from 0.85 → 0.70 (industry standard)
- Expected impact: Escalation rate 60% → 25-30%
- Expected savings: ~40% cost reduction

**2. Removed Person Count Limit**
- Removed escalation trigger at 25+ people
- Comprehensive extraction no longer punished
- Aligns system behavior with stated goals

**Cost Impact**:
```
Before Optimization:
  40% × $0.02 (Haiku) + 60% × $0.08 (Sonnet) = $0.056/newsletter

After Optimization:
  75% × $0.02 (Haiku) + 25% × $0.08 (Sonnet) = $0.035/newsletter

Savings: $0.021/newsletter (37% reduction)
Annual Savings: ~$153 at 20 newsletters/day
```

#### Validation Framework

Created comprehensive validation system for ground truth testing:
- Manual annotation templates (JSON & CSV)
- Automated metrics calculation script
- Detailed validation guide
- Example annotations

**To Run Validation**:
1. Annotate 3-5 newsletters using templates in `validation/ground_truth/`
2. Run `python validation/calculate_metrics.py`
3. Review results in `validation/results/validation_report.md`

#### Production Readiness Status

**Current Status**: ❌ NOT READY FOR PRODUCTION

| Requirement | Target | Current | Status |
|------------|--------|---------|--------|
| Official F1 Score | >0.80 | ~0.38 | ❌ Failed |
| Journalist Coverage | >0.70 | ~0.15 | ❌ Failed |
| Escalation Rate | <30% | 60% → 25%* | ⚠️ Improving |
| Cost Efficiency | <$0.04 | $0.056 → $0.035* | ⚠️ Improving |

*After optimization (testing in progress)

**Estimated Time to Production**: 4-6 weeks
- Week 1: Validation testing with optimized settings
- Week 2-3: Prompt optimization to improve recall
- Week 4: Final testing and production decision

### Future Multi-Stage Enhancement Plan

#### Phase 2: Ultra-Low Cost Pre-filtering (Future)
- **Stage 0**: Groq/Gemini Flash pre-filter ($0.002/newsletter)
- **Stage 1**: Haiku validation ($0.008/newsletter)  
- **Stage 2**: Sonnet resolution ($0.003 average)
- **Target**: 99.9% accuracy at $0.013/newsletter

#### Phase 3: Real-Time Verification (Future)
- Political database integration
- Current role verification via Perplexity API
- Continuous learning pipeline

#### Phase 4: Advanced Analytics (Future)
- Network analysis and relationship graphs
- Temporal relationship tracking
- Political influence mapping

## Outstanding Issues (Updated November 2025)

### Critical Priority
- **LOW RECALL RATES**: Claude NLP processor only capturing 11-36% of mentioned entities (target: 70%+)
  - Journalists severely under-detected (~10-20% vs target 70%+)
  - Political staff routinely missed (~5-15%)
  - Requires prompt optimization and potentially model adjustments

- **NULL FIELD PROBLEM**: CA Playbook extraction produced entities with almost all fields NULL despite 0.92 confidence
  - Indicates confidence scores don't reflect extraction quality
  - May require separate quality validation step

### Medium Priority
- **Playbook Type Mapping**: Email-to-playbook-type mapping in `html_to_json.py` needs refinement
  - Should be based on content analysis rather than assumptions

- **Escalation Testing Needed**: Optimized thresholds implemented but not yet validated
  - Need to measure actual escalation rate with 0.70 threshold
  - Verify person count limit removal doesn't cause issues

### Resolved ✅
- ✅ **Escalation Logic Paradox**: Fixed - removed 25-person limit
- ✅ **High Confidence Threshold**: Fixed - lowered from 0.85 to 0.70
- ✅ **No Validation Framework**: Fixed - comprehensive validation system created
- ✅ **Cost Overruns**: Fixed - expected 37% cost reduction after optimization

## Updated Dependencies

```txt
# Core dependencies
requests==2.31.0
beautifulsoup4==4.12.2
python-dotenv==1.0.0
pandas==2.1.4
lxml==4.9.3

# AI/NLP APIs
anthropic>=0.18.0       # Claude API for NLP extraction

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

**Environment Variables Required**:
```bash
# .env file
GMAIL_USER=your_email@gmail.com           # For email extraction
GMAIL_PASSWORD=your_app_password          # Gmail app-specific password
ANTHROPIC_API_KEY=sk-ant-xxx              # Claude API for NLP processing
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