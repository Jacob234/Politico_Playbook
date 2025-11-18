#!/usr/bin/env python3
"""
Calculate precision, recall, and F1 scores by comparing ground truth annotations
to Claude NLP processor output.

Usage:
    python calculate_metrics.py

The script will:
1. Load all ground truth files from ground_truth/
2. Load corresponding Claude processor outputs
3. Match entities between ground truth and system output
4. Calculate metrics by category and overall
5. Generate detailed comparison report
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re


@dataclass
class EntityMatch:
    """Represents a match between ground truth and system output."""
    name: str
    category: str
    match_type: str  # 'true_positive', 'false_positive', 'false_negative'
    ground_truth_data: Dict = None
    system_data: Dict = None


@dataclass
class CategoryMetrics:
    """Metrics for a specific entity category."""
    category: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    def calculate(self):
        """Calculate precision, recall, and F1 score."""
        # Precision: TP / (TP + FP)
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)
        else:
            self.precision = 0.0

        # Recall: TP / (TP + FN)
        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)
        else:
            self.recall = 0.0

        # F1: 2 * (P * R) / (P + R)
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0


def normalize_name(name: str) -> str:
    """Normalize names for matching (remove titles, lowercase, strip whitespace)."""
    # Remove common titles
    name = re.sub(r'\b(Sen\.|Rep\.|Dr\.|Mr\.|Mrs\.|Ms\.|Gov\.|Pres\.|Secretary)\s*', '', name, flags=re.IGNORECASE)
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Lowercase for comparison
    return name.lower().strip()


def names_match(name1: str, name2: str) -> bool:
    """Check if two names refer to the same person."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match
    if norm1 == norm2:
        return True

    # Check if one is substring of other (handles "John Thune" vs "Thune")
    if norm1 in norm2 or norm2 in norm1:
        # Make sure it's not a very short match
        shorter = min(len(norm1), len(norm2))
        if shorter > 3:  # Require at least 4 characters
            return True

    # Check if last names match (split and compare last word)
    parts1 = norm1.split()
    parts2 = norm2.split()
    if len(parts1) > 0 and len(parts2) > 0:
        if parts1[-1] == parts2[-1] and len(parts1[-1]) > 3:
            return True

    return False


def load_ground_truth(file_path: Path) -> Dict:
    """Load ground truth annotations from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def load_system_output(file_path: Path) -> Dict:
    """Load Claude NLP processor output from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
        # Extract claude_nlp_results if present
        if 'claude_nlp_results' in data:
            return data['claude_nlp_results']
        return data


def match_entities(ground_truth: List[Dict], system_output: List[Dict]) -> List[EntityMatch]:
    """Match entities between ground truth and system output."""
    matches = []
    gt_matched = set()
    sys_matched = set()

    # Find true positives (entities in both)
    for i, gt_entity in enumerate(ground_truth):
        for j, sys_entity in enumerate(system_output):
            if j in sys_matched:
                continue

            # Check if names match
            if names_match(gt_entity['name'], sys_entity['name']):
                # Check if categories match
                if gt_entity['category'] == sys_entity['category']:
                    # True positive - correct extraction
                    matches.append(EntityMatch(
                        name=gt_entity['name'],
                        category=gt_entity['category'],
                        match_type='true_positive',
                        ground_truth_data=gt_entity,
                        system_data=sys_entity
                    ))
                    gt_matched.add(i)
                    sys_matched.add(j)
                    break
                else:
                    # Wrong category - counts as both FP and FN
                    matches.append(EntityMatch(
                        name=sys_entity['name'],
                        category=sys_entity['category'],
                        match_type='false_positive',
                        ground_truth_data=gt_entity,
                        system_data=sys_entity
                    ))
                    matches.append(EntityMatch(
                        name=gt_entity['name'],
                        category=gt_entity['category'],
                        match_type='false_negative',
                        ground_truth_data=gt_entity,
                        system_data=sys_entity
                    ))
                    gt_matched.add(i)
                    sys_matched.add(j)
                    break

    # Find false negatives (in ground truth but not extracted)
    for i, gt_entity in enumerate(ground_truth):
        if i not in gt_matched:
            matches.append(EntityMatch(
                name=gt_entity['name'],
                category=gt_entity['category'],
                match_type='false_negative',
                ground_truth_data=gt_entity,
                system_data=None
            ))

    # Find false positives (extracted but not in ground truth)
    for j, sys_entity in enumerate(system_output):
        if j not in sys_matched:
            matches.append(EntityMatch(
                name=sys_entity['name'],
                category=sys_entity.get('category', 'unknown'),
                match_type='false_positive',
                ground_truth_data=None,
                system_data=sys_entity
            ))

    return matches


def calculate_metrics_by_category(matches: List[EntityMatch]) -> Dict[str, CategoryMetrics]:
    """Calculate metrics for each entity category."""
    categories = defaultdict(lambda: CategoryMetrics(category=''))

    for match in matches:
        cat = match.category
        if cat not in categories:
            categories[cat] = CategoryMetrics(category=cat)

        if match.match_type == 'true_positive':
            categories[cat].true_positives += 1
        elif match.match_type == 'false_positive':
            categories[cat].false_positives += 1
        elif match.match_type == 'false_negative':
            categories[cat].false_negatives += 1

    # Calculate metrics for each category
    for cat_metrics in categories.values():
        cat_metrics.calculate()

    return dict(categories)


def calculate_overall_metrics(category_metrics: Dict[str, CategoryMetrics]) -> CategoryMetrics:
    """Calculate overall metrics across all categories."""
    overall = CategoryMetrics(category='overall')

    for metrics in category_metrics.values():
        overall.true_positives += metrics.true_positives
        overall.false_positives += metrics.false_positives
        overall.false_negatives += metrics.false_negatives

    overall.calculate()
    return overall


def generate_report(results: Dict) -> str:
    """Generate a human-readable markdown report."""
    report = []
    report.append("# Claude NLP Processor - Validation Results")
    report.append("")
    report.append(f"**Validation Date**: {results['validation_date']}")
    report.append(f"**Newsletters Evaluated**: {results['newsletters_evaluated']}")
    report.append("")
    report.append("---")
    report.append("")

    # Overall metrics
    report.append("## Overall Performance")
    report.append("")
    overall = results['overall_metrics']
    report.append(f"| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| **Precision** | {overall['precision']:.2%} |")
    report.append(f"| **Recall** | {overall['recall']:.2%} |")
    report.append(f"| **F1 Score** | {overall['f1_score']:.3f} |")
    report.append(f"| True Positives | {overall['true_positives']} |")
    report.append(f"| False Positives | {overall['false_positives']} |")
    report.append(f"| False Negatives | {overall['false_negatives']} |")
    report.append("")

    # Status assessment
    f1 = overall['f1_score']
    if f1 >= 0.80:
        status = "✅ **EXCELLENT** - Production ready"
    elif f1 >= 0.70:
        status = "✅ **GOOD** - Acceptable for production"
    elif f1 >= 0.60:
        status = "⚠️ **FAIR** - Needs improvement before production"
    elif f1 >= 0.50:
        status = "⚠️ **POOR** - Significant optimization required"
    else:
        status = "❌ **INADEQUATE** - Major rework needed"

    report.append(f"**Status**: {status}")
    report.append("")
    report.append("---")
    report.append("")

    # By category
    report.append("## Performance by Entity Category")
    report.append("")
    report.append("| Category | Precision | Recall | F1 Score | TP | FP | FN |")
    report.append("|----------|-----------|--------|----------|----|----|-----|")

    for cat_name, metrics in results['category_metrics'].items():
        report.append(
            f"| {cat_name} | {metrics['precision']:.2%} | "
            f"{metrics['recall']:.2%} | {metrics['f1_score']:.3f} | "
            f"{metrics['true_positives']} | {metrics['false_positives']} | "
            f"{metrics['false_negatives']} |"
        )

    report.append("")
    report.append("---")
    report.append("")

    # Per newsletter results
    report.append("## Results by Newsletter")
    report.append("")

    for newsletter_result in results['newsletter_results']:
        report.append(f"### {newsletter_result['newsletter_file']}")
        report.append(f"**Type**: {newsletter_result['newsletter_type']}")
        report.append(f"**Subject**: {newsletter_result['subject_line']}")
        report.append("")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Precision | {newsletter_result['precision']:.2%} |")
        report.append(f"| Recall | {newsletter_result['recall']:.2%} |")
        report.append(f"| F1 Score | {newsletter_result['f1_score']:.3f} |")
        report.append(f"| Ground Truth Entities | {newsletter_result['ground_truth_count']} |")
        report.append(f"| System Extracted | {newsletter_result['system_count']} |")
        report.append(f"| Correctly Matched | {newsletter_result['true_positives']} |")
        report.append("")

    report.append("---")
    report.append("")

    # Recommendations
    report.append("## Recommendations")
    report.append("")

    if overall['recall'] < 0.70:
        report.append("### Critical Issue: Low Recall")
        report.append(f"- Current recall: {overall['recall']:.2%} (Target: 70%+)")
        report.append("- System is missing too many entities")
        report.append("- **Action**: Optimize prompts to capture more entities")
        report.append("")

    if overall['precision'] < 0.90:
        report.append("### Issue: Low Precision")
        report.append(f"- Current precision: {overall['precision']:.2%} (Target: 90%+)")
        report.append("- System is extracting incorrect entities")
        report.append("- **Action**: Add validation rules or improve confidence scoring")
        report.append("")

    # Category-specific recommendations
    for cat_name, metrics in results['category_metrics'].items():
        if metrics['f1_score'] < 0.60:
            report.append(f"### Issue: Poor {cat_name} Detection")
            report.append(f"- F1 Score: {metrics['f1_score']:.3f} (Target: 0.70+)")
            report.append(f"- Precision: {metrics['precision']:.2%}, Recall: {metrics['recall']:.2%}")
            report.append(f"- **Action**: Review prompt for {cat_name} entity extraction")
            report.append("")

    return "\n".join(report)


def main():
    """Main validation pipeline."""
    print("Claude NLP Processor - Validation Metrics Calculator")
    print("=" * 60)
    print()

    # Set up directories
    validation_dir = Path(__file__).parent
    ground_truth_dir = validation_dir / "ground_truth"
    results_dir = validation_dir / "results"
    claude_enhanced_dir = validation_dir.parent / "data" / "claude_enhanced"

    # Create results directory if it doesn't exist
    results_dir.mkdir(exist_ok=True)

    # Check if ground truth directory exists
    if not ground_truth_dir.exists():
        print(f"❌ Ground truth directory not found: {ground_truth_dir}")
        print("Please create ground truth annotations first.")
        print(f"See VALIDATION_GUIDE.md for instructions.")
        return

    # Find all ground truth files
    gt_files = list(ground_truth_dir.glob("*_ground_truth.json"))

    if not gt_files:
        print(f"❌ No ground truth files found in {ground_truth_dir}")
        print("Please create at least one ground truth annotation.")
        print(f"Use validation_template.json as a starting point.")
        return

    print(f"Found {len(gt_files)} ground truth file(s)")
    print()

    # Process each ground truth file
    all_results = {
        'validation_date': '2025-11-18',
        'newsletters_evaluated': len(gt_files),
        'newsletter_results': [],
        'category_metrics': {},
        'overall_metrics': {}
    }

    all_matches = []

    for gt_file in gt_files:
        print(f"Processing: {gt_file.name}")

        # Load ground truth
        try:
            gt_data = load_ground_truth(gt_file)
        except Exception as e:
            print(f"  ❌ Error loading ground truth: {e}")
            continue

        # Find corresponding system output
        newsletter_file = gt_data['newsletter_file']
        system_file = claude_enhanced_dir / f"claude_test_{newsletter_file}"

        if not system_file.exists():
            # Try without claude_test_ prefix
            system_file = claude_enhanced_dir / newsletter_file

        if not system_file.exists():
            print(f"  ⚠️  System output not found: {system_file.name}")
            print(f"      Skipping this newsletter")
            continue

        # Load system output
        try:
            sys_data = load_system_output(system_file)
        except Exception as e:
            print(f"  ❌ Error loading system output: {e}")
            continue

        # Match entities
        gt_entities = gt_data['ground_truth_entities']
        sys_entities = sys_data.get('people', [])

        matches = match_entities(gt_entities, sys_entities)
        all_matches.extend(matches)

        # Calculate metrics for this newsletter
        newsletter_metrics = calculate_metrics_by_category(matches)
        overall_newsletter = calculate_overall_metrics(newsletter_metrics)

        # Store results
        newsletter_result = {
            'newsletter_file': newsletter_file,
            'newsletter_type': gt_data.get('newsletter_type', 'unknown'),
            'subject_line': gt_data.get('subject_line', ''),
            'ground_truth_count': len(gt_entities),
            'system_count': len(sys_entities),
            'true_positives': overall_newsletter.true_positives,
            'false_positives': overall_newsletter.false_positives,
            'false_negatives': overall_newsletter.false_negatives,
            'precision': overall_newsletter.precision,
            'recall': overall_newsletter.recall,
            'f1_score': overall_newsletter.f1_score
        }
        all_results['newsletter_results'].append(newsletter_result)

        print(f"  ✅ Precision: {overall_newsletter.precision:.2%}, "
              f"Recall: {overall_newsletter.recall:.2%}, "
              f"F1: {overall_newsletter.f1_score:.3f}")
        print()

    if not all_matches:
        print("❌ No matches found. Check that system output files exist.")
        return

    # Calculate overall metrics
    print("Calculating overall metrics...")
    all_results['category_metrics'] = {
        cat: asdict(metrics)
        for cat, metrics in calculate_metrics_by_category(all_matches).items()
    }

    overall_metrics = calculate_overall_metrics(
        {cat: CategoryMetrics(**metrics) for cat, metrics in all_results['category_metrics'].items()}
    )
    all_results['overall_metrics'] = asdict(overall_metrics)

    # Save results
    results_file = results_dir / "validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"✅ Results saved to: {results_file}")

    # Generate report
    report = generate_report(all_results)
    report_file = results_dir / "validation_report.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"✅ Report saved to: {report_file}")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Precision: {overall_metrics.precision:.2%}")
    print(f"Recall: {overall_metrics.recall:.2%}")
    print(f"F1 Score: {overall_metrics.f1_score:.3f}")
    print()

    if overall_metrics.f1_score >= 0.70:
        print("✅ System meets production standards (F1 >= 0.70)")
    else:
        print(f"❌ System below production standards (F1 = {overall_metrics.f1_score:.3f}, target >= 0.70)")

    print()
    print("Review validation_report.md for detailed analysis and recommendations.")


if __name__ == "__main__":
    main()
