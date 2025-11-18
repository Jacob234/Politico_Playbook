# Politico Web Scraper - Comprehensive Implementation Plan

## Executive Summary

This plan outlines the design and implementation of a web scraper to extract Politico Playbook newsletters directly from Politico's website, as an alternative or complement to the current Gmail-based extraction system.

**Current State**: Email extraction via Gmail IMAP (20 newsletters collected)
**Proposed State**: Web scraping from politico.com with automated scheduling
**Timeline**: 2-3 weeks development + 1 week testing
**Complexity**: Medium-High (legal, technical, rate limiting considerations)

---

## Table of Contents

1. [Research Findings](#research-findings)
2. [Legal & Ethical Considerations](#legal--ethical-considerations)
3. [Technical Requirements](#technical-requirements)
4. [Architecture Design](#architecture-design)
5. [Implementation Plan](#implementation-plan)
6. [Testing Strategy](#testing-strategy)
7. [Risk Assessment & Mitigation](#risk-assessment--mitigation)
8. [Alternatives & Recommendations](#alternatives--recommendations)

---

## Research Findings

### Politico Newsletter Structure

Based on research:

1. **Publication Locations**:
   - Newsletters are published on politico.com/newsletters/playbook/
   - Individual editions have URLs like: `politico.com/newsletters/playbook/YYYY/MM/DD/[article-slug]`
   - Example: `politico.com/newsletters/playbook/2025/08/01/republicans-summer-shindig`

2. **Newsletter Variants**:
   From existing data, we've identified:
   - National Playbook (main edition)
   - State Playbooks: New York, Florida, California
   - Specialized: Politico Pulse, Politico Nightly
   - Others: West Wing Playbook, Brussels Playbook, etc.

3. **Access Methods**:
   - Public web pages (accessible without subscription for some content)
   - Email subscription (current method)
   - Politico Pro (paid subscription, enhanced access)
   - Archive at Annenberg Public Policy Center
   - Library of Congress Web Archives

4. **Publishing Schedule**:
   - Daily publication (Monday-Friday for most editions)
   - Morning delivery (~6-7 AM ET typical)
   - Some editions publish in afternoon/evening

### Content Structure

Newsletters typically contain:
- Subject line / headline
- Authors / byline
- Sponsor information
- Main body text (HTML formatted)
- Inline links to articles
- Newsletter-specific branding
- Footer with subscription management

---

## Legal & Ethical Considerations

### ⚠️ CRITICAL: Must Review Before Implementation

#### 1. Terms of Service Compliance

**Required Actions**:
- ✅ **MUST DO**: Review Politico's Terms of Service at politico.com/terms-of-service
- ✅ **MUST DO**: Check robots.txt at politico.com/robots.txt
- ✅ **MUST DO**: Verify copyright and fair use provisions

**Potential Issues**:
- Commercial use restrictions
- Automated access prohibitions
- Rate limiting requirements
- Attribution requirements

#### 2. Ethical Web Scraping Principles

**Best Practices to Follow**:
1. **Respect robots.txt**: Always check and comply with crawl directives
2. **Rate Limiting**: Implement generous delays between requests (2-5 seconds minimum)
3. **User-Agent**: Identify scraper honestly with contact information
4. **Off-Peak Hours**: Schedule scraping during low-traffic periods
5. **Caching**: Never re-fetch already downloaded content
6. **Attribution**: Maintain clear source attribution in stored data

#### 3. Copyright Considerations

**Important**:
- Politico content is copyrighted
- Fair use may apply for:
  - Research purposes
  - Personal use
  - Educational applications
  - Non-commercial analysis

**Not Permitted**:
- Republishing full content commercially
- Creating competing newsletter service
- Mass redistribution without permission

**Recommendation**: For commercial use, contact Politico for API access or licensing.

#### 4. Alternative: Official API

**Research Needed**:
- Check if Politico offers an official API
- Politico Pro subscribers may have enhanced access
- Contact Politico developer relations: developers@politico.com (verify actual contact)

---

## Technical Requirements

### Prerequisites

#### 1. Python Libraries

```python
# Core scraping
requests>=2.31.0           # HTTP requests
beautifulsoup4>=4.12.2     # HTML parsing
lxml>=4.9.3                # Fast XML/HTML processing

# Advanced scraping (if needed)
selenium>=4.15.0           # JavaScript rendering (if required)
playwright>=1.40.0         # Modern browser automation (alternative)

# Utilities
python-dotenv>=1.0.0       # Environment variables
schedule>=1.2.0            # Task scheduling
retry>=0.9.2               # Retry logic for failed requests

# Data handling (already have)
pandas>=2.1.4
```

#### 2. System Requirements

- **Internet Connection**: Stable, reliable
- **Storage**: Minimal (HTML newsletters ~50-100KB each)
- **Processing**: Low (simple HTML parsing)
- **Scheduling**: Cron job or Python scheduler

#### 3. Environment Variables

```bash
# Add to .env file
POLITICO_USER_AGENT="YourOrganization Bot (contact@example.com)"
POLITICO_REQUEST_DELAY=3  # Seconds between requests
POLITICO_MAX_RETRIES=3
POLITICO_TIMEOUT=30       # Request timeout in seconds
```

### Technical Challenges

#### Challenge 1: Dynamic Content

**Issue**: Some newsletters may use JavaScript rendering
**Detection**: Check if content appears in HTML source
**Solutions**:
- **Option A**: Use requests + BeautifulSoup (if content is in HTML)
- **Option B**: Use Selenium/Playwright (if JavaScript required)
- **Option C**: Find RSS/Atom feeds (if available)

#### Challenge 2: URL Discovery

**Issue**: Need to find newsletter URLs for each edition
**Possible Approaches**:
1. **Pattern-based**: Generate URLs from known patterns
2. **Archive crawling**: Start from archive page, follow links
3. **RSS feed**: Subscribe to RSS if available
4. **Sitemap**: Check sitemap.xml for newsletter URLs

#### Challenge 3: Authentication

**Issue**: Some content may be paywalled
**Mitigation**:
- Check if newsletters are publicly accessible
- If paywalled, consider Politico Pro subscription
- Alternatively, stick with email extraction for paywalled content

#### Challenge 4: Rate Limiting & IP Blocking

**Issue**: Excessive requests may trigger blocks
**Mitigation**:
- Implement exponential backoff
- Use respectful request delays (3-5 seconds)
- Rotate user-agents (cautiously)
- Monitor for 429 (Too Many Requests) responses
- Implement circuit breaker pattern

---

## Architecture Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     POLITICO WEB SCRAPER                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    1. URL DISCOVERY MODULE                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Archive      │  │ Pattern Gen  │  │  RSS Feed    │      │
│  │ Crawler      │  │              │  │  Parser      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  2. CONTENT FETCHER MODULE                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │  • Rate limiting (3-5s delay)                     │       │
│  │  • Retry logic (3 attempts, exponential backoff) │       │
│  │  • User-Agent management                         │       │
│  │  • Caching (avoid re-downloads)                  │       │
│  │  • robots.txt compliance                         │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   3. HTML PARSER MODULE                      │
│  ┌──────────────────────────────────────────────────┐       │
│  │  Extract:                                         │       │
│  │  • Subject line / headline                        │       │
│  │  • Authors                                        │       │
│  │  • Publication date                               │       │
│  │  • Newsletter type                                │       │
│  │  • Main content (clean HTML)                      │       │
│  │  • Plain text version                             │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                4. STORAGE & DEDUPLICATION                    │
│  ┌──────────────────────────────────────────────────┐       │
│  │  • Check if already downloaded (hash comparison)  │       │
│  │  • Save raw HTML → data/raw/                      │       │
│  │  • Save to structured JSON → data/structured/     │       │
│  │  • Update metadata database                       │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  5. SCHEDULER & MONITORING                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │  • Daily scheduled runs (7 AM ET)                 │       │
│  │  • Error logging                                  │       │
│  │  • Success/failure notifications                  │       │
│  │  • Metrics tracking (download count, errors)      │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Module Specifications

#### Module 1: URL Discovery

**File**: `politico_playbook/src/extraction/web_url_discoverer.py`

**Responsibilities**:
- Generate URLs for newsletters based on patterns
- Crawl archive pages to find newsletter links
- Parse RSS feeds if available
- Maintain list of discovered URLs

**Key Functions**:
```python
def discover_playbook_urls(date_range, newsletter_type='national'):
    """Discover Playbook URLs for given date range."""

def generate_url_patterns(date, newsletter_type):
    """Generate possible URL patterns for a newsletter."""

def crawl_archive_page(archive_url):
    """Extract newsletter links from archive page."""
```

#### Module 2: Content Fetcher

**File**: `politico_playbook/src/extraction/web_fetcher.py`

**Responsibilities**:
- Fetch web pages with rate limiting
- Handle retries and errors
- Respect robots.txt
- Manage HTTP sessions
- Cache responses

**Key Functions**:
```python
class PoliticoWebFetcher:
    def __init__(self, delay=3, max_retries=3):
        """Initialize fetcher with rate limiting."""

    def fetch_url(self, url, cache=True):
        """Fetch URL with rate limiting and retry logic."""

    def check_robots_txt(self, url):
        """Verify URL is allowed by robots.txt."""

    def get_cached(self, url):
        """Retrieve from cache if available."""
```

#### Module 3: HTML Parser

**File**: `politico_playbook/src/extraction/web_parser.py`

**Responsibilities**:
- Parse Politico newsletter HTML
- Extract metadata (title, authors, date)
- Extract main content
- Convert to structured format
- Handle different newsletter layouts

**Key Functions**:
```python
class PoliticoNewsletterParser:
    def parse_newsletter(self, html_content, url):
        """Parse newsletter HTML into structured data."""

    def extract_metadata(self, soup):
        """Extract title, authors, date, type."""

    def extract_content(self, soup):
        """Extract main newsletter content."""

    def detect_newsletter_type(self, soup, url):
        """Determine newsletter type (National, NY, FL, etc.)."""
```

#### Module 4: Storage Manager

**File**: `politico_playbook/src/extraction/web_storage.py`

**Responsibilities**:
- Store raw HTML
- Save structured JSON
- Detect duplicates
- Update metadata database

**Key Functions**:
```python
def save_newsletter(html, parsed_data, url):
    """Save newsletter to filesystem."""

def is_duplicate(url, content_hash):
    """Check if newsletter already downloaded."""

def update_metadata_db(newsletter_data):
    """Update metadata tracking database."""
```

#### Module 5: Scheduler

**File**: `politico_playbook/src/extraction/web_scheduler.py`

**Responsibilities**:
- Schedule daily scraping runs
- Handle errors and retries
- Log results
- Send notifications

**Key Functions**:
```python
def schedule_daily_scrape(time='07:00', timezone='US/Eastern'):
    """Schedule daily newsletter scraping."""

def run_scraper():
    """Execute full scraping workflow."""

def send_notification(success, stats):
    """Notify about scraping results."""
```

---

## Implementation Plan

### Phase 1: Research & Validation (Week 1, Days 1-2)

#### Tasks:
1. **Legal Review** ⚠️ CRITICAL
   - [ ] Read Politico Terms of Service
   - [ ] Check robots.txt compliance
   - [ ] Verify copyright/fair use applicability
   - [ ] Document findings and get approval

2. **Technical Reconnaissance**
   - [ ] Visit politico.com/newsletters/playbook/
   - [ ] Inspect HTML structure of 3-5 newsletters
   - [ ] Test if content loads without JavaScript
   - [ ] Check for RSS/Atom feeds
   - [ ] Identify URL patterns
   - [ ] Test sample fetch with curl/requests

3. **Architecture Validation**
   - [ ] Confirm newsletter accessibility (public vs. paywalled)
   - [ ] Test rate limiting (manual requests)
   - [ ] Verify data structure matches email format

**Deliverables**:
- Legal compliance document (GO/NO-GO decision)
- HTML structure analysis document
- URL pattern documentation
- Proof-of-concept fetch script

### Phase 2: Core Development (Week 1, Days 3-7)

#### Day 3-4: URL Discovery & Fetcher

**Tasks**:
- [ ] Implement `web_url_discoverer.py`
  - Pattern-based URL generation
  - Date range handling
  - Newsletter type mapping
- [ ] Implement `web_fetcher.py`
  - Rate-limited HTTP client
  - Retry logic with exponential backoff
  - robots.txt checker
  - Response caching
- [ ] Write unit tests for both modules

**Acceptance Criteria**:
- Can generate URLs for last 30 days
- Can fetch pages with 3-second delays
- Respects robots.txt rules
- Retries failed requests up to 3 times

#### Day 5-6: Parser & Storage

**Tasks**:
- [ ] Implement `web_parser.py`
  - HTML parsing with BeautifulSoup
  - Metadata extraction
  - Content cleaning
  - Newsletter type detection
- [ ] Implement `web_storage.py`
  - Deduplication logic
  - File naming conventions
  - JSON structuring
  - Metadata database
- [ ] Write unit tests

**Acceptance Criteria**:
- Parses all newsletter types correctly
- Extracts clean text and structured data
- Matches email extraction format
- Detects and skips duplicates

#### Day 7: Integration

**Tasks**:
- [ ] Create main scraper script
- [ ] Integrate all modules
- [ ] Add logging and monitoring
- [ ] Test end-to-end workflow
- [ ] Handle edge cases and errors

**Acceptance Criteria**:
- Can scrape 10 newsletters without errors
- Logs detailed progress and errors
- Produces output matching email format
- Gracefully handles failures

### Phase 3: Scheduling & Automation (Week 2, Days 1-2)

**Tasks**:
- [ ] Implement `web_scheduler.py`
- [ ] Add cron job / systemd timer configuration
- [ ] Implement notification system (email/Slack)
- [ ] Add monitoring dashboard (optional)
- [ ] Document deployment process

**Acceptance Criteria**:
- Runs automatically daily at 7 AM ET
- Sends success/failure notifications
- Logs to file and console
- Can be manually triggered for testing

### Phase 4: Testing & Validation (Week 2, Days 3-5)

**Tasks**:
- [ ] Run scraper for 1 week, compare with email extraction
- [ ] Verify data quality and completeness
- [ ] Test error handling (network failures, rate limits)
- [ ] Validate against existing email-based data
- [ ] Performance testing (memory, speed)

**Acceptance Criteria**:
- 95%+ success rate over 1 week
- Output matches email format exactly
- No duplicate downloads
- Handles errors gracefully

### Phase 5: Documentation & Handoff (Week 2, Day 6-7)

**Tasks**:
- [ ] Write user documentation
- [ ] Create troubleshooting guide
- [ ] Document deployment process
- [ ] Update CLAUDE.md with web scraper info
- [ ] Create comparison: email vs. web scraping

**Deliverables**:
- User guide
- Admin guide
- API documentation
- Updated project docs

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 80%+

**Test Files**:
```
politico_playbook/tests/extraction/
├── test_web_url_discoverer.py
├── test_web_fetcher.py
├── test_web_parser.py
├── test_web_storage.py
└── test_web_scheduler.py
```

**Key Test Cases**:

#### URL Discovery
- [ ] Generate URLs for various date ranges
- [ ] Handle different newsletter types
- [ ] Validate URL format
- [ ] Handle invalid dates

#### Fetcher
- [ ] Respect rate limiting
- [ ] Retry on failures
- [ ] Handle timeouts
- [ ] Check robots.txt compliance
- [ ] Cache responses correctly

#### Parser
- [ ] Extract metadata correctly
- [ ] Handle malformed HTML
- [ ] Detect newsletter types
- [ ] Clean content appropriately
- [ ] Match email format output

#### Storage
- [ ] Detect duplicates
- [ ] Save to correct directories
- [ ] Generate valid JSON
- [ ] Update metadata database

### Integration Tests

**Test Scenarios**:
1. **Happy Path**: Scrape 5 newsletters successfully
2. **Network Failure**: Handle connection errors
3. **Rate Limiting**: Respect delays and retry
4. **Duplicate Detection**: Skip already-downloaded newsletters
5. **Malformed Content**: Handle parsing errors gracefully

### Validation Tests

**Compare Web Scraper vs. Email Extraction**:
- Same content extracted?
- Same metadata captured?
- Same JSON structure?
- Similar processing time?

---

## Risk Assessment & Mitigation

### Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation |
|------|-------------|--------|----------|------------|
| **Legal/ToS Violation** | Medium | Critical | **HIGH** | Review ToS, get legal approval, implement compliance |
| **IP Blocking** | Medium | High | **MEDIUM** | Rate limiting, respectful delays, monitoring |
| **Content Changes** | High | Medium | **MEDIUM** | Flexible parsing, version detection, alerts |
| **Paywall Introduced** | Low | High | **MEDIUM** | Fallback to email, subscription option |
| **API Availability** | Low | Low | **LOW** | Use official API if available |
| **Data Quality Issues** | Medium | Medium | **MEDIUM** | Validation against email data, quality checks |

### Detailed Risk Mitigation

#### Risk 1: Legal/Terms of Service Violation

**Mitigation Strategy**:
1. **Pre-Implementation**:
   - Formal review of Politico ToS
   - Document fair use justification
   - Consider contacting Politico for permission
   - Check if API available

2. **During Implementation**:
   - Strict robots.txt compliance
   - Respectful rate limiting
   - Clear user-agent identification
   - No circumvention of access controls

3. **Post-Implementation**:
   - Monitor for cease-and-desist notices
   - Be prepared to switch back to email
   - Maintain audit trail of compliance

**Fallback**: Continue using email extraction if web scraping not permitted

#### Risk 2: IP Blocking / Rate Limiting

**Mitigation Strategy**:
1. **Prevention**:
   - Generous delays (3-5 seconds minimum)
   - Exponential backoff on retries
   - Schedule during off-peak hours (early morning)
   - Limit concurrent requests to 1

2. **Detection**:
   - Monitor for 429 (Too Many Requests) responses
   - Detect 403 (Forbidden) patterns
   - Track request success rates

3. **Response**:
   - Implement circuit breaker pattern
   - Automatically increase delays if blocked
   - Alert administrator
   - Fallback to email extraction

**Fallback**: Dual system (email + web) with automatic failover

#### Risk 3: Website Structure Changes

**Mitigation Strategy**:
1. **Flexible Parsing**:
   - Use multiple selector strategies
   - Implement version detection
   - Graceful degradation

2. **Monitoring**:
   - Validate extracted data
   - Alert on parsing failures
   - Compare with email data

3. **Maintenance**:
   - Regular parser updates
   - Version control for parsers
   - Quick response to changes

**Fallback**: Temporarily revert to email extraction during fixes

#### Risk 4: Paywall Introduction

**Mitigation Strategy**:
1. **Detection**:
   - Monitor for paywall indicators
   - Check content completeness
   - Compare with email versions

2. **Options**:
   - Subscribe to Politico Pro
   - Use authenticated session
   - Revert to email extraction

**Fallback**: Email extraction is unaffected by web paywalls

---

## Alternatives & Recommendations

### Alternative 1: Official API ⭐ RECOMMENDED

**Description**: Use Politico's official API if available

**Pros**:
- ✅ Legally compliant
- ✅ Reliable and stable
- ✅ Better rate limits
- ✅ Structured data format
- ✅ Support available

**Cons**:
- ❌ May require subscription
- ❌ May have costs
- ❌ Limited to API features

**Recommendation**: **Research first** - contact Politico about API access

**Action**: Email developers@politico.com or check developer docs

### Alternative 2: RSS/Atom Feeds ⭐⭐ HIGHLY RECOMMENDED

**Description**: Subscribe to RSS feeds if Politico provides them

**Pros**:
- ✅ Designed for consumption
- ✅ Legally compliant
- ✅ Easy to parse
- ✅ Real-time updates
- ✅ Low complexity

**Cons**:
- ❌ May not include full content
- ❌ Availability uncertain

**Recommendation**: **Check for RSS feeds** before building scraper

**Action**: Check for RSS links in newsletter pages or politico.com/feeds

### Alternative 3: Continue Email Extraction

**Description**: Keep using current Gmail-based system

**Pros**:
- ✅ Already working
- ✅ Legally compliant (your email)
- ✅ Complete content
- ✅ No rate limiting concerns
- ✅ Zero additional development

**Cons**:
- ❌ Requires email subscription
- ❌ Depends on Gmail API
- ❌ Potential delays in delivery

**Recommendation**: **Best current option** unless API/RSS available

### Alternative 4: Hybrid Approach ⭐⭐⭐ BEST OF BOTH WORLDS

**Description**: Use email as primary, web scraper as backup/supplement

**Pros**:
- ✅ Redundancy
- ✅ Fill gaps in email collection
- ✅ Validate email data
- ✅ Access historical archives

**Cons**:
- ❌ More complexity
- ❌ Duplicate management needed

**Recommendation**: **Ideal solution** - web scraper for historical + email for daily

### Alternative 5: Third-Party Data Services

**Description**: Use existing political newsletter aggregators

**Pros**:
- ✅ Already licensed
- ✅ Clean data
- ✅ API access

**Cons**:
- ❌ Expensive
- ❌ May not have Playbook
- ❌ Vendor lock-in

**Recommendation**: Consider for commercial deployment

---

## Final Recommendations

### Recommended Approach (Priority Order)

#### 1. ⭐ FIRST: Research Official Access

**Action Items**:
- [ ] Search for Politico API documentation
- [ ] Check for RSS/Atom feeds
- [ ] Email Politico developer relations
- [ ] Check Politico Pro subscription benefits

**Timeline**: 1-2 days
**Effort**: Low
**Risk**: Low

**If Found**: Use official method (stop here, best solution)

#### 2. ⭐⭐ SECOND: Legal Review

**Action Items**:
- [ ] Review Terms of Service thoroughly
- [ ] Check robots.txt
- [ ] Document fair use justification
- [ ] Get legal approval if available

**Timeline**: 2-3 days
**Effort**: Low-Medium
**Risk**: Low

**If Approved**: Proceed to web scraper development
**If Not Approved**: Continue with email extraction

#### 3. ⭐⭐⭐ THIRD: Implement Hybrid System

**Recommended Architecture**:
```
┌─────────────────────────────────────────┐
│         PRIMARY: Email Extraction        │
│  • Daily collection (current system)     │
│  • Reliable, compliant, complete         │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│      SECONDARY: Web Scraper (Limited)    │
│  • Historical backfill only              │
│  • Low frequency (weekly/monthly)        │
│  • Gap filling for missed emails         │
│  • Respectful, minimal impact            │
└─────────────────────────────────────────┘
```

**Benefits**:
- Keep working email system
- Add web scraper for specific use cases:
  - Historical backfill (pre-subscription)
  - Fill gaps from missed emails
  - Validation/comparison
- Minimize legal/ethical concerns (low frequency)
- Best of both worlds

### Implementation Recommendation

**DO NOT** build a full daily web scraper yet. Instead:

**Phase 1**: Continue with email extraction (working well)
**Phase 2**: Research official API/RSS
**Phase 3**: If needed, build limited web scraper for historical backfill only
**Phase 4**: Monitor and maintain

**Rationale**:
- Email extraction is working (20 newsletters collected successfully)
- Web scraping has legal/ethical risks
- Official API would be better if available
- Historical backfill is the real value-add (not daily scraping)

---

## Budget & Resource Requirements

### Development Time

| Phase | Duration | Effort |
|-------|----------|--------|
| Legal Review & Research | 3-5 days | 16-24 hours |
| Core Development | 5-7 days | 30-40 hours |
| Testing & Validation | 3-5 days | 16-24 hours |
| Documentation | 1-2 days | 4-8 hours |
| **Total** | **2-3 weeks** | **66-96 hours** |

### Infrastructure Costs

- **Hosting**: $0 (runs on existing infrastructure)
- **Storage**: Negligible (~100MB/year for newsletters)
- **API Costs**: $0 (if using web scraping)
- **Subscription**: $0-$500/year (if Politico Pro needed)

### Maintenance

- **Ongoing**: 2-4 hours/month (monitoring, updates)
- **Parser Updates**: 4-8 hours/quarter (if website changes)

---

## Success Metrics

### Key Performance Indicators

1. **Collection Success Rate**: >95% of published newsletters
2. **Timeliness**: Collect within 24 hours of publication
3. **Data Quality**: 100% match with email format
4. **Uptime**: 99%+ availability
5. **Error Rate**: <5% failed requests
6. **Legal Compliance**: Zero violations

### Monitoring Dashboard

**Recommended Metrics**:
- Newsletters collected (daily/weekly/monthly)
- Success/failure rate
- Average fetch time
- Error types and frequency
- Storage usage
- Rate limit encounters

---

## Next Steps

### Immediate (This Week)

1. **Decision Point**: Review this plan with stakeholders
2. **Legal Review**: Assign someone to review Politico ToS
3. **API Research**: Check for official Politico API
4. **RSS Research**: Look for newsletter RSS feeds

### Short Term (Next 2 Weeks)

If GO decision:
1. Set up development environment
2. Begin Phase 1 implementation
3. Build proof-of-concept

If NO-GO decision:
1. Document reasons
2. Enhance email extraction system
3. Research alternative sources

### Long Term (Next 3 Months)

1. Monitor web scraper performance
2. Optimize and refine
3. Expand to additional newsletter types
4. Build monitoring dashboard

---

## Appendix

### Useful Resources

1. **Web Scraping Best Practices**:
   - https://www.scrapingbee.com/blog/web-scraping-best-practices/
   - https://developers.google.com/search/docs/advanced/guidelines/webmaster-guidelines

2. **Legal Resources**:
   - Fair Use guidelines: https://www.copyright.gov/fair-use/
   - EFF on web scraping: https://www.eff.org/issues/coders/reverse-engineering-faq

3. **Technical Resources**:
   - BeautifulSoup docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
   - Requests docs: https://requests.readthedocs.io/
   - Scrapy framework: https://scrapy.org/ (if scaling up)

### Sample Code Snippets

#### Basic Fetcher (Proof of Concept)

```python
import requests
import time
from bs4 import BeautifulSoup

class PoliticoFetcher:
    def __init__(self, delay=3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ResearchBot/1.0 (contact@example.com)',
        })
        self.delay = delay
        self.last_request = 0

    def fetch(self, url):
        # Rate limiting
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.last_request = time.time()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

# Usage
fetcher = PoliticoFetcher(delay=3)
html = fetcher.fetch('https://www.politico.com/newsletters/playbook/')
if html:
    soup = BeautifulSoup(html, 'lxml')
    # Parse content...
```

---

**Document Version**: 1.0
**Date**: November 18, 2025
**Author**: Claude Code Agent
**Status**: Draft for Review
**Next Review**: After legal review completion
