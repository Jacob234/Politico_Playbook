# Claude NLP Processor - Validation Guide

## Overview

This guide provides a systematic approach to creating ground truth annotations for measuring the true performance of the Claude NLP processor. By manually annotating newsletters, we can calculate accurate precision, recall, and F1 scores.

---

## Validation Methodology

### Goals
1. **Measure True Performance**: Calculate precision, recall, and F1 scores
2. **Identify Failure Patterns**: Understand which entity types are missed
3. **Validate Improvements**: Compare before/after optimization metrics
4. **Set Baselines**: Establish minimum acceptable performance standards

### Approach
1. **Select Representative Sample**: 3-5 newsletters covering different types
2. **Manual Annotation**: Identify ALL people mentioned in each newsletter
3. **Compare to System Output**: Match ground truth against Claude extractions
4. **Calculate Metrics**: Precision, recall, F1 for each entity category
5. **Analyze Gaps**: Document patterns in missed entities

---

## Entity Categories

Use these categories when annotating (aligned with Claude processor output):

| Category | Description | Examples |
|----------|-------------|----------|
| **political_official** | Elected officials, appointed leaders | Senators, Representatives, Governors, Cabinet members, Mayors |
| **journalist** | Reporters, correspondents, news writers | Newsletter authors, cited reporters, news anchors |
| **political_staff** | Political staff, advisors, aides | Chiefs of Staff, Press Secretaries, Campaign managers, Advisors |
| **lobbyist** | Industry representatives, advocates | Registered lobbyists, advocacy group leaders |
| **business_leader** | Corporate executives in political context | CEOs mentioned for policy relevance, Industry spokespeople |
| **other** | Public figures, experts, citizens | Academics, activists, general public |

### Entity Inclusion Rules

**INCLUDE if**:
- ✅ Person is named explicitly (first and last name, or last name with title)
- ✅ Person has relevance to political/policy content
- ✅ Person is mentioned in substantive context (not just photo credits)

**EXCLUDE if**:
- ❌ Only first name mentioned without clear identity
- ❌ Historical figures not relevant to current events
- ❌ Generic references ("unnamed sources", "administration officials")
- ❌ Photo credits, footer signatures, newsletter templates

### Special Cases

**Newsletter Authors**: Always include as `journalist` category

**People Mentioned Multiple Times**: Count only once in ground truth

**Former Officials**: Include if still politically relevant
- Example: "Former VP Kamala Harris" → Include as political_official
- Example: "George Washington" in historical context → Exclude

**Reporters Cited**: Include when named
- Example: "POLITICO's Carmen Paun reports..." → Include Carmen Paun as journalist

**Ambiguous Names**: When in doubt, include if context suggests relevance

---

## Annotation Process

### Step 1: Read Newsletter Completely
- Understand the full context
- Note major storylines and key figures
- Identify all person mentions

### Step 2: Create Initial List
- Read through again systematically (top to bottom)
- Record every person mentioned
- Note line numbers or context for reference

### Step 3: Categorize Each Person
- Assign category (political_official, journalist, etc.)
- Note their role/title if mentioned
- Record relevant context (what they did/said)

### Step 4: Quality Check
- Verify no duplicates
- Confirm all names have categories
- Check that inclusions meet rules above

### Step 5: Document in Template
- Use provided JSON or CSV template
- Include confidence in categorization (if uncertain)
- Add notes for edge cases

---

## Validation Templates

### JSON Format (Recommended)

```json
{
  "newsletter_file": "2025-08-01_110122_email.json",
  "newsletter_type": "florida_playbook",
  "subject_line": "Republicans' summer shindig",
  "annotator": "Your Name",
  "annotation_date": "2025-11-18",
  "ground_truth_entities": [
    {
      "name": "Evan Power",
      "category": "political_official",
      "role": "Republican Party of Florida Chair",
      "party": "Republican",
      "state": "Florida",
      "context": "Organizing Florida Freedom Forum, expanding party meeting access",
      "line_reference": "Near beginning, mentioned multiple times",
      "confidence": 1.0,
      "notes": ""
    },
    {
      "name": "Kimberly Leonard",
      "category": "journalist",
      "role": "Reporter",
      "employer": "POLITICO",
      "context": "Newsletter author",
      "line_reference": "Byline",
      "confidence": 1.0,
      "notes": "Author of newsletter"
    },
    {
      "name": "Byron Donalds",
      "category": "political_official",
      "role": "U.S. Representative, Gubernatorial candidate",
      "party": "Republican",
      "state": "Florida",
      "context": "Speaking at Florida Freedom Forum, running for governor",
      "line_reference": "Middle section, 'Republican heavyweights'",
      "confidence": 1.0,
      "notes": ""
    }
  ],
  "total_entities": 27,
  "entity_breakdown": {
    "political_official": 18,
    "journalist": 6,
    "political_staff": 3,
    "business_leader": 0,
    "other": 0
  },
  "annotation_time_minutes": 45,
  "notes": "Very dense newsletter with many officials mentioned. Some reporters only cited by last name."
}
```

### CSV Format (Alternative)

Use this if you prefer spreadsheet annotation:

```csv
name,category,role,party,state,employer,context,line_reference,confidence,notes
Evan Power,political_official,RPOF Chair,Republican,Florida,,Organizing Florida Freedom Forum,Beginning section,1.0,
Ron DeSantis,political_official,Governor,Republican,Florida,,Speaking at forum,Middle section,1.0,
Kimberly Leonard,journalist,Reporter,,,POLITICO,Newsletter author,Byline,1.0,Author
Byron Donalds,political_official,Representative,Republican,Florida,,Gov candidate speaking at forum,Middle section,1.0,
```

**CSV Template**: `validation_template.csv` (provided in this directory)

---

## Calculating Metrics

### Definitions

**True Positives (TP)**: Entities correctly extracted by Claude (present in both ground truth and system output)

**False Positives (FP)**: Entities extracted by Claude but not in ground truth (system hallucinations or wrong categorizations)

**False Negatives (FN)**: Entities in ground truth but missed by Claude (recall failures)

### Formulas

```
Precision = TP / (TP + FP)
  → Of all entities Claude extracted, what % were correct?

Recall = TP / (TP + FN)
  → Of all entities that should be extracted, what % did Claude find?

F1 Score = 2 × (Precision × Recall) / (Precision + Recall)
  → Harmonic mean balancing precision and recall
```

### Matching Rules

**Exact Match**: Same name, same category → Count as TP

**Partial Match**: Same person but wrong category → Count as FP and FN
- Example: Claude extracts "Laura Loomer" as journalist, but ground truth says political_staff
- This is wrong extraction (FP) AND missed correct categorization (FN)

**Name Variations**: Use judgment
- "John Thune" vs "Sen. Thune" → Same person, count as match
- "Katie Porter" vs "Rep. Porter" → Same person, count as match

---

## Sample Size Recommendations

### Minimum Sample (Quick Assessment)
- **3 newsletters**: 1 National, 1 State, 1 Specialized
- **Time**: ~2-3 hours total
- **Purpose**: Get rough performance estimate

### Standard Sample (Statistical Validity)
- **5 newsletters**: Mix of types, ensuring coverage
- **Time**: ~3-5 hours total
- **Purpose**: Reliable metrics for production decision

### Comprehensive Sample (Full Validation)
- **10-15 newsletters**: Representative of actual usage
- **Time**: ~8-12 hours total
- **Purpose**: Complete system characterization

---

## Using the Validation Script

### Step 1: Annotate Newsletters

Use the JSON or CSV template to create ground truth files:

```
politico_playbook/validation/ground_truth/
├── 2025-08-01_110122_email_ground_truth.json
├── 2025-08-01_130047_email_ground_truth.json
├── 2025-08-01_140058_email_ground_truth.json
└── ...
```

### Step 2: Run Validation Script

```bash
cd politico_playbook
python validation/calculate_metrics.py
```

The script will:
1. Load ground truth annotations
2. Load Claude processor outputs
3. Match entities between them
4. Calculate precision, recall, F1 scores
5. Generate detailed comparison report

### Step 3: Review Results

The script outputs:
- `validation_results.json`: Detailed metrics by category
- `validation_report.md`: Human-readable summary
- `confusion_matrix.csv`: Entity matching analysis

---

## Validation Checklist

### Before Starting
- [ ] Read this entire guide
- [ ] Understand entity categories
- [ ] Set up templates (JSON or CSV)
- [ ] Select 3-5 representative newsletters

### During Annotation
- [ ] Read newsletter completely first
- [ ] Annotate systematically (top to bottom)
- [ ] Record all required fields
- [ ] Note edge cases and uncertainties
- [ ] Track time spent per newsletter

### After Annotation
- [ ] Quality check for duplicates
- [ ] Verify all entities have categories
- [ ] Count totals by category
- [ ] Run validation script
- [ ] Review and document findings

---

## Quality Assurance

### Inter-Annotator Agreement (Optional)

For higher confidence, have 2-3 people annotate the same newsletter independently:

1. Each annotator creates their own ground truth
2. Compare annotations
3. Discuss discrepancies
4. Create consensus ground truth
5. Calculate inter-annotator agreement (Cohen's Kappa)

**Target Agreement**: >80% for reliable validation

### Common Pitfalls

❌ **Inconsistent categorization**: Using different categories for similar roles
- Fix: Review category definitions before each session

❌ **Missing newsletter authors**: Forgetting to include journalists in byline
- Fix: Always check byline first

❌ **Including template text**: Counting people in footers/boilerplate
- Fix: Only count substantive content

❌ **Overlooking cited reporters**: Missing "POLITICO's John Doe reports"
- Fix: Search for reporter citations explicitly

---

## Expected Results

Based on preliminary analysis, expect to find:

### Precision (Current)
- Political Officials: 95-99% (high)
- Journalists: 80-90% (good)
- Overall: 95%+ (high)

### Recall (Current - Before Optimization)
- Political Officials: 25-40% (low)
- Journalists: 10-20% (very low)
- Political Staff: 5-15% (very low)
- Overall: 20-35% (low)

### F1 Scores (Current)
- Political Officials: 0.40-0.55 (poor to fair)
- Journalists: 0.15-0.30 (poor)
- Overall: 0.35-0.45 (poor)

### After Optimization (Target)
- Overall Precision: 90%+ (maintain high)
- Overall Recall: 70%+ (major improvement needed)
- Overall F1: 0.80+ (production standard)

---

## Using Results

### Production Readiness Decision

**GO if**:
- F1 score >0.70 for political officials
- F1 score >0.60 for journalists
- Precision >90% overall
- Recall >70% overall

**NO-GO if**:
- F1 score <0.60 overall
- Recall <50% (missing half of entities)
- Critical entity types consistently missed

**CONDITIONAL if**:
- Some metrics met, others close
- Clear path to improvement identified
- Acceptable for limited/pilot deployment

---

## Next Steps After Validation

1. **Document Findings**: Update performance report with real metrics
2. **Identify Patterns**: Analyze which entities are systematically missed
3. **Optimize Prompts**: Target specific failure modes
4. **Re-test**: Measure improvement after optimization
5. **Iterate**: Repeat until production standards met

---

## Support Files

This directory contains:
- `VALIDATION_GUIDE.md` (this file)
- `validation_template.json` (JSON annotation template)
- `validation_template.csv` (CSV annotation template)
- `calculate_metrics.py` (automated metric calculation script)
- `ground_truth/` (directory for annotations)
- `results/` (directory for validation outputs)

---

## Questions?

Refer to:
- `claude_nlp_analysis_2025-11-18.md` for detailed performance findings
- `claude_nlp_processor.py` for system implementation details
- `OPTIMIZATION_SUMMARY.md` for context on current state

---

**Last Updated**: November 18, 2025
**Version**: 1.0
**Status**: Ready for use
