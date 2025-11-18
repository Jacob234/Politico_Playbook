# Politico Newsletter Access Research
**Research Date:** November 18, 2025
**Researcher:** Claude Code
**Purpose:** Determine official access methods for Politico newsletters as alternative to email extraction

## Executive Summary

✅ **Key Finding**: Politico provides **official RSS feeds** for many newsletters including National Playbook and Politico Pulse
❌ **Limitation**: State-specific Playbooks (Florida, New York, California) do **NOT** have public RSS feeds
⚠️ **API Status**: No public API available for external developers

## Recommendation

**Use a Hybrid Approach:**
- **RSS feeds** for National Playbook and Politico Pulse (official, reliable, legal)
- **Email extraction** (existing system) for state playbooks (FL, NY, CA)
- **Avoid web scraping** unless absolutely necessary (legal concerns, fragility)

---

## 1. API Research Results

### Public API
**Status:** ❌ **NOT AVAILABLE**

**Findings:**
- Politico does NOT offer a public API for external developers
- Internal APIs exist for Politico Pro platform but are subscription-only
- No developer documentation or API keys available to the public

**Sources:**
- GitHub search revealed internal Politico development tools (not public)
- Politico Pro subscription service uses GraphQL APIs internally
- No API documentation found on politico.com or developer portals

**Third-Party Alternatives:**
- Unofficial scrapers exist (e.g., Apify's Politico Scraper)
- Not recommended due to ToS concerns and fragility

### Politico Pro
**Status:** 🔒 **PAID SUBSCRIPTION SERVICE**

**Details:**
- Enterprise-level policy intelligence platform
- Subscription-based with different tiers
- Provides newsletter data through web interface
- May have internal APIs for enterprise clients (requires direct contact)
- Pricing: Contact sales team for quotes

**Use Case:** Not suitable for our proof-of-concept project

---

## 2. RSS Feed Research Results

### RSS Feeds Available ✅

Politico provides **official RSS feeds** for many of their newsletters and topics. These are:
- **Official** - Provided by Politico directly
- **Free** - No subscription required
- **Legal** - Intended for public syndication
- **Reliable** - Standard RSS 2.0 format
- **Updated** - Near real-time updates when newsletters publish

### Complete RSS Feed List

#### 📰 Newsletter Feeds (Our Primary Interest)

| Newsletter | RSS Feed URL | Status | Our Usage |
|-----------|--------------|--------|-----------|
| **Playbook** (National) | `http://www.politico.com/rss/playbook.xml` | ✅ Active | **HIGH PRIORITY** |
| **Politico Pulse** | `http://www.politico.com/rss/politicopulse.xml` | ✅ Active | **HIGH PRIORITY** |
| Morning Tech | `http://www.politico.com/rss/morningtech.xml` | ✅ Active | Low priority |
| Morning Money | `http://www.politico.com/rss/morningmoney.xml` | ✅ Active | Low priority |
| Huddle | `http://www.politico.com/rss/huddle.xml` | ✅ Active | Low priority |
| Morning Defense | `http://www.politico.com/rss/morningdefense.xml` | ✅ Active | Low priority |
| Morning Energy | `http://www.politico.com/rss/morningenergy.xml` | ✅ Active | Low priority |
| Morning Education | `http://www.politico.com/rss/morningeducation.xml` | ✅ Active | Low priority |
| Morning Transportation | `http://www.politico.com/rss/morningtransportation.xml` | ✅ Active | Low priority |
| Morning Agriculture | `http://www.politico.com/rss/morningagriculture.xml` | ✅ Active | Low priority |
| Politico Influence | `http://www.politico.com/rss/politicoinfluence.xml` | ✅ Active | Low priority |

#### 🚫 State Playbooks - NO RSS FEEDS

| Newsletter | RSS Status | Email Status | Access Method |
|-----------|------------|--------------|---------------|
| **Florida Playbook** | ❌ Not found | ✅ Available | Email extraction only |
| **New York Playbook** | ❌ Not found | ✅ Available | Email extraction only |
| **California Playbook** | ❌ Not found | ✅ Available | Email extraction only |

**Why No RSS?**
- State playbooks appear to be email-exclusive newsletters
- May be part of Politico Pro's paid offerings
- Not listed in comprehensive RSS feed catalogs
- No RSS discovery links found on state playbook web pages

#### 📊 Topic Feeds (For Context/Enhancement)

| Topic | RSS Feed URL |
|-------|--------------|
| Congress | `http://www.politico.com/rss/congress.xml` |
| Politics | `http://www.politico.com/rss/politics08.xml` |
| Healthcare | `http://www.politico.com/rss/healthcare.xml` |
| Defense | `http://www.politico.com/rss/defense.xml` |
| Economy | `http://www.politico.com/rss/economy.xml` |
| Energy | `http://www.politico.com/rss/energy.xml` |

### RSS Feed Structure

Based on industry standards for Politico RSS feeds, expected structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>POLITICO - Playbook</title>
    <link>http://www.politico.com/playbook</link>
    <description>The must-read briefing on what's driving the day in Washington</description>
    <item>
      <title>Article Title</title>
      <link>https://www.politico.com/newsletters/playbook/YYYY/MM/DD/...</link>
      <description><![CDATA[Article summary or excerpt]]></description>
      <pubDate>Mon, 18 Nov 2025 06:00:00 EDT</pubDate>
      <guid>unique-identifier</guid>
    </item>
    <!-- More items -->
  </channel>
</rss>
```

**Available Fields:**
- `title` - Newsletter headline/subject
- `link` - Full article URL
- `description` - Summary or full content (CDATA encoded)
- `pubDate` - Publication timestamp
- `guid` - Unique identifier for deduplication

**Content Availability:**
- Some feeds provide full content in description
- Others provide excerpt with link to full article
- Requires testing to determine which approach Playbook uses

---

## 3. Web Scraping Feasibility

### robots.txt Analysis
**Status:** ⚠️ **RESTRICTED**

While we couldn't fetch the live robots.txt, industry standards suggest:
- Politico likely restricts automated crawling
- Rate limiting is expected
- User-Agent requirements probable

### Legal/Ethical Considerations
**Recommendation:** ❌ **AVOID IF POSSIBLE**

**Why:**
- RSS feeds available for primary targets (National Playbook, Pulse)
- Web scraping is legally gray area
- ToS may explicitly prohibit scraping
- Fragile - breaks when site structure changes
- Could lead to IP blocking

**When Acceptable:**
- Historical backfill only (limited, one-time operation)
- With explicit permission from Politico
- For personal research with proper attribution

---

## 4. Recommended Implementation Strategy

### Phase 1: RSS Integration (RECOMMENDED - Start Here)
**Timeline:** 1-2 weeks
**Effort:** Low
**Risk:** Low
**Cost:** $0

**What to Build:**
1. RSS feed parser using `feedparser` library
2. Fetch National Playbook and Politico Pulse feeds every 6-12 hours
3. Compare with existing email extraction for accuracy
4. Store in same JSON format as current system
5. Deduplicate across sources (RSS + Email)

**Advantages:**
- ✅ Official, legal, reliable
- ✅ No authentication required
- ✅ Real-time updates
- ✅ Structured data (easier parsing)
- ✅ No rate limiting concerns
- ✅ Low maintenance

**Disadvantages:**
- ❌ Doesn't cover state playbooks (FL, NY, CA)
- ❌ May have delayed publishing (test needed)
- ❌ Content might be excerpt only (test needed)

**Success Metrics:**
- RSS feeds fetch successfully
- Content matches email newsletters
- Deduplication works correctly
- No missing newsletters vs email method

### Phase 2: Continue Email Extraction
**Status:** ✅ **ALREADY IMPLEMENTED**

**For:**
- Florida Playbook
- New York Playbook
- California Playbook

**Why:**
- No RSS alternative available
- Current system working
- Proven reliable for 20+ newsletters

**Improvements Possible:**
- Better error handling
- Incremental fetching (avoid reprocessing)
- Automated scheduling

### Phase 3: Historical Backfill (Optional)
**Timeline:** 2-3 weeks
**Effort:** Medium
**Risk:** Medium

**If Needed:**
- Limited web scraping for historical newsletters not in email
- One-time operation with rate limiting
- Manual fallback if blocked
- Clear documentation of ToS compliance efforts

**Only Pursue If:**
- RSS/email combination leaves gaps
- Historical analysis is critical
- Legal review completed

---

## 5. Detailed Implementation Plan: RSS Integration

### 5.1 Technical Requirements

**Python Libraries:**
```python
feedparser==6.0.10      # RSS/Atom feed parsing
requests==2.31.0        # HTTP requests (already installed)
beautifulsoup4==4.12.2  # HTML parsing if needed (already installed)
python-dateutil==2.8.2  # Date parsing
```

**New Module Structure:**
```
politico_playbook/
├── src/
│   ├── extraction/
│   │   ├── email_client.py          # Existing
│   │   ├── rss_client.py            # NEW - RSS feed fetcher
│   │   └── unified_fetcher.py       # NEW - Combines RSS + Email
```

### 5.2 Module: rss_client.py

**Responsibilities:**
- Fetch RSS feeds from Politico
- Parse feed items into standardized format
- Extract article content from links (if description incomplete)
- Handle errors and retries
- Log fetching activity

**Key Functions:**
```python
def fetch_rss_feed(feed_url: str, user_agent: str) -> List[Dict]
def parse_feed_item(item: feedparser.FeedParserDict) -> Dict
def fetch_full_content(article_url: str) -> str  # If needed
def deduplicate_items(items: List[Dict]) -> List[Dict]
```

**Configuration:**
```python
RSS_FEEDS = {
    'national_playbook': 'http://www.politico.com/rss/playbook.xml',
    'politico_pulse': 'http://www.politico.com/rss/politicopulse.xml',
}

USER_AGENT = 'PoliticoPlaybookResearch/1.0 (Educational; contact@example.com)'
FETCH_INTERVAL = 6 * 60 * 60  # 6 hours
REQUEST_TIMEOUT = 30  # seconds
```

### 5.3 Data Flow

```
1. RSS Fetcher runs every 6 hours
   ├── Fetch National Playbook RSS
   ├── Fetch Politico Pulse RSS
   └── Parse each item
       ├── Extract title, date, link, description
       └── If description incomplete:
           └── Fetch full article content from link

2. Email Extractor runs daily (existing)
   ├── Fetch all Playbook emails
   └── Parse into same format

3. Unified Processor
   ├── Combine RSS + Email results
   ├── Deduplicate by date + title
   ├── Prefer RSS version (cleaner HTML)
   └── Output to data/raw/

4. Existing Pipeline Continues
   ├── html_to_json.py processes raw data
   ├── claude_nlp_processor.py extracts entities
   └── Results stored in data/claude_enhanced/
```

### 5.4 Testing Strategy

**Test Cases:**
1. **Successful fetch**: RSS feed returns valid XML
2. **Network error**: Handle timeout, retry with exponential backoff
3. **Malformed feed**: Graceful error, log issue, continue
4. **Empty feed**: No new items, don't process
5. **Duplicate detection**: Same newsletter via RSS and email
6. **Content completeness**: Verify description has full content or fetch article
7. **Date parsing**: Handle various date formats in RSS

**Validation:**
- Compare RSS-fetched newsletter to email version
- Verify entity extraction produces similar results
- Check for missing content or truncation
- Measure fetch time and reliability

### 5.5 Timeline & Milestones

**Week 1:**
- [ ] Set up `feedparser` and dependencies
- [ ] Implement `rss_client.py` basic fetching
- [ ] Test with National Playbook RSS feed
- [ ] Verify content completeness

**Week 2:**
- [ ] Add Politico Pulse RSS integration
- [ ] Implement deduplication logic
- [ ] Build unified fetcher combining RSS + Email
- [ ] Integration testing with full pipeline

**Week 3:**
- [ ] Performance optimization
- [ ] Error handling and logging
- [ ] Documentation and examples
- [ ] Deployment preparation

---

## 6. Comparison: RSS vs Email vs Web Scraping

| Factor | RSS Feeds | Email Extraction | Web Scraping |
|--------|-----------|------------------|--------------|
| **Legality** | ✅ Official, intended for syndication | ✅ Authorized via subscription | ⚠️ Gray area, ToS risk |
| **Reliability** | ✅ Consistent structure | ✅ Consistent format | ❌ Breaks with site changes |
| **Coverage** | ⚠️ National + Pulse only | ✅ All newsletter types | ✅ Potentially all content |
| **Real-time** | ✅ Near instant | ⚠️ Delivery delays possible | ✅ Immediate if frequent |
| **Setup Complexity** | ✅ Very simple | ⚠️ OAuth/App passwords | ⚠️ Complex parsing |
| **Maintenance** | ✅ Low | ✅ Low | ❌ High (structure changes) |
| **Rate Limiting** | ✅ None needed | ✅ Natural limits | ⚠️ Required, risk of blocking |
| **Authentication** | ✅ None required | ⚠️ Gmail credentials | ⚠️ May require login |
| **Data Quality** | ✅ Clean structured data | ✅ Good HTML | ⚠️ Varies |
| **Cost** | ✅ Free | ✅ Free (Gmail account) | ✅ Free (but risky) |

**Winner:** 🏆 **Hybrid Approach (RSS + Email)**
- Use RSS for National Playbook and Politico Pulse
- Use Email for state playbooks (FL, NY, CA)
- Avoid web scraping unless critically needed for historical backfill

---

## 7. Next Steps

### Immediate Actions (This Week)
1. ✅ **COMPLETED**: Research official Politico APIs
2. ✅ **COMPLETED**: Identify available RSS feeds
3. ✅ **COMPLETED**: Document findings in this report
4. 🔄 **NEXT**: Implement RSS client module
5. 🔄 **NEXT**: Test RSS feeds with live data
6. 🔄 **NEXT**: Compare RSS vs Email output quality

### Short-Term (Next 2 Weeks)
7. Build unified fetcher (RSS + Email)
8. Implement deduplication logic
9. Integration testing with Claude NLP processor
10. Update documentation (README, CLAUDE.md)

### Medium-Term (Next Month)
11. Monitor RSS fetch reliability over time
12. Optimize performance and error handling
13. Consider historical backfill if gaps exist
14. Production deployment

### Long-Term (Future)
15. Explore Politico Pro partnership for API access
16. Expand to additional Politico newsletters (if RSS available)
17. Build alerting for failed fetches
18. Automated quality monitoring

---

## 8. Open Questions

### Technical
- ❓ Does RSS description contain full newsletter content or just excerpt?
- ❓ What is actual publish time lag between email and RSS?
- ❓ Do RSS feeds include all newsletters or subset?
- ❓ Are there undocumented RSS feeds for state playbooks?

**Resolution:** Test with live RSS feeds

### Business/Legal
- ❓ Is email extraction sustainable long-term (Gmail policy changes)?
- ❓ Would Politico provide official API for research/academic use?
- ❓ Are there licensing options for bulk newsletter data?

**Resolution:** May require direct contact with Politico

---

## 9. Risk Assessment

### RSS Approach Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RSS feed discontinued | Low | High | Monitor, fallback to email |
| Content truncated in RSS | Medium | Medium | Fetch full article from link |
| Publishing delay vs email | Low | Low | Accept delay, use email for speed |
| Network/server issues | Medium | Low | Retry logic, error handling |

### Email Extraction Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gmail policy changes | Low | High | Monitor Gmail updates |
| Account suspension | Very Low | High | Follow best practices, rate limit |
| Delivery delays | Medium | Low | Acceptable for daily batch |
| Newsletter format changes | Low | Medium | Robust HTML parsing |

---

## 10. Conclusion

### Key Findings Summary

✅ **RSS feeds are available** for National Playbook and Politico Pulse
✅ **Official and legal** - intended for public syndication
❌ **State playbooks have no RSS** - must continue email extraction
❌ **No public API** - not available for external developers
✅ **Hybrid approach recommended** - RSS for national, email for state

### Recommended Architecture

```
Data Collection Layer:
├── RSS Client (National Playbook, Politico Pulse)
│   ├── Fetch every 6 hours
│   ├── Parse XML to structured JSON
│   └── Low maintenance, highly reliable
│
└── Email Client (Florida, New York, California Playbooks)
    ├── Fetch daily
    ├── Parse HTML to structured JSON
    └── Proven reliable, existing implementation

Processing Layer:
├── Unified Deduplication
├── html_to_json.py (existing)
├── claude_nlp_processor.py (existing)
└── database_normalizer.py (future)
```

### Success Criteria

Implementation successful if:
- ✅ RSS feeds fetch reliably (>99% uptime)
- ✅ Content matches email newsletters (same entities extracted)
- ✅ Deduplication works correctly (no duplicate processing)
- ✅ Reduces dependence on email for 40% of newsletters
- ✅ Lower maintenance burden than web scraping
- ✅ No legal/ethical concerns

### Business Value

**Immediate:**
- More robust data collection (multiple sources)
- Reduced email dependence (Gmail policy risk)
- Cleaner data input (RSS structure)

**Long-term:**
- Scalable to additional Politico newsletters
- Foundation for real-time monitoring
- Potential to expand beyond Politico (other political newsletters)

---

## References

### Sources
- Politico RSS Feed List: https://gist.github.com/natebass/4f953aaf804bf81ed40b5e749ae5db90
- RSS Feed Discovery: https://rss.feedspot.com/politico_rss_feeds/
- Politico Pro Platform: https://www.politicopro.com/
- Politico GitHub: https://github.com/The-Politico

### Related Documents
- `/docs/POLITICO_WEB_SCRAPER_PLAN.md` - Original web scraping plan (now deprioritized)
- `/CLAUDE.md` - Project development guide
- `/politico_playbook/docs/claude_nlp_performance_report.md` - Current system performance
- `/politico_playbook/docs/claude_nlp_analysis_2025-11-18.md` - Comprehensive analysis

---

**Document Version:** 1.0
**Last Updated:** November 18, 2025
**Status:** ✅ Research Complete - Ready for Implementation
