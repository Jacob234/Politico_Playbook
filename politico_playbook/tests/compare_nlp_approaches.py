#!/usr/bin/env python3
"""
Compare spaCy vs Claude NLP approaches for political newsletter analysis.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from src.processing.claude_nlp_processor import ClaudeNLPProcessor

# Load environment variables from .env file
load_dotenv()


def compare_approaches():
    """Compare spaCy and Claude NLP results on same newsletter."""
    
    base_dir = Path(__file__).parent
    
    # Load sample newsletter
    structured_dir = base_dir / "data" / "structured"
    sample_file = structured_dir / "2025-08-01_085105_email.json"
    
    # Load existing spaCy results
    spacy_enhanced_dir = base_dir / "data" / "structured" / "nlp_enhanced"
    spacy_file = spacy_enhanced_dir / "2025-08-01_085105_email_nlp.json"
    
    print("🔬 Comparing NLP Approaches")
    print("=" * 50)
    
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return
    
    # Load newsletter data
    with open(sample_file, 'r', encoding='utf-8') as f:
        newsletter_data = json.load(f)
    
    print(f"Newsletter: {newsletter_data.get('subject_line', 'Unknown')}")
    print(f"Text length: {len(newsletter_data.get('text', ''))} characters")
    
    # Load spaCy results if available
    spacy_results = None
    if spacy_file.exists():
        with open(spacy_file, 'r', encoding='utf-8') as f:
            spacy_data = json.load(f)
            spacy_results = spacy_data.get('nlp_results', {})
    
    # Process with Claude (if API key available)
    claude_results = None
    if os.getenv("ANTHROPIC_API_KEY"):
        print("\n🤖 Processing with Claude...")
        try:
            processor = ClaudeNLPProcessor()
            enhanced_data = processor.process_newsletter(newsletter_data.copy())
            claude_results = enhanced_data.get('claude_nlp_results', {})
            
            # Save Claude results for later analysis
            claude_output_dir = base_dir / "data" / "structured" / "claude_enhanced"
            os.makedirs(claude_output_dir, exist_ok=True)
            claude_output_file = claude_output_dir / f"claude_{sample_file.name}"
            
            with open(claude_output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Claude results saved to: {claude_output_file}")
            
        except Exception as e:
            print(f"❌ Claude processing error: {e}")
    else:
        print("⚠️  ANTHROPIC_API_KEY not set - skipping Claude processing")
    
    # Compare results
    print("\n📊 COMPARISON RESULTS")
    print("=" * 50)
    
    if spacy_results:
        spacy_entities = spacy_results.get('entities', {})
        spacy_persons = spacy_entities.get('persons', [])
        spacy_relationships = spacy_results.get('relationships', [])
        
        print(f"\n🔬 spaCy Results:")
        print(f"  Persons: {len(spacy_persons)}")
        print(f"  Relationships: {len(spacy_relationships)}")
        print(f"  Sample persons:")
        for person in spacy_persons[:5]:
            titles = ', '.join(person.get('titles', []))
            party = person.get('party', 'Unknown')
            conf = person.get('confidence', 0)
            print(f"    - {person['name']} ({titles}) [{party}] (conf: {conf:.2f})")
    
    if claude_results:
        claude_people = claude_results.get('people', [])
        claude_relationships = claude_results.get('relationships', [])
        claude_organizations = claude_results.get('organizations', [])
        claude_stories = claude_results.get('stories_and_topics', [])
        
        print(f"\n🤖 Claude Comprehensive Results:")
        print(f"  People: {len(claude_people)}")
        print(f"  Relationships: {len(claude_relationships)}")
        print(f"  Organizations: {len(claude_organizations)}")
        print(f"  Stories/Topics: {len(claude_stories)}")
        
        # Show sample people by category
        political_officials = [p for p in claude_people if p.get('category') == 'political_official']
        journalists = [p for p in claude_people if p.get('category') == 'journalist']
        staff = [p for p in claude_people if p.get('category') in ['staff', 'political_staff']]
        
        print(f"\n  Political Officials ({len(political_officials)}):")
        for person in political_officials[:3]:
            role = person.get('role', 'Unknown')
            party = person.get('party', 'Unknown')
            conf = person.get('confidence', 0)
            print(f"    - {person['name']} ({role}) [{party}] (conf: {conf:.2f})")
        
        print(f"\n  Journalists ({len(journalists)}):")
        for person in journalists[:3]:
            employer = person.get('employer', 'Unknown')
            reported_on = ', '.join(person.get('reported_on', []))[:50] + ('...' if len(', '.join(person.get('reported_on', []))) > 50 else '')
            conf = person.get('confidence', 0)
            print(f"    - {person['name']} ({employer}) reported on: {reported_on} (conf: {conf:.2f})")
        
        print(f"\n  Staff/Others ({len(staff)}):")
        for person in staff[:3]:
            role = person.get('role', 'Unknown')
            employer = person.get('employer', 'Unknown')
            conf = person.get('confidence', 0)
            print(f"    - {person['name']} ({role} at {employer}) (conf: {conf:.2f})")
        
        processing_info = claude_results.get('processing_info', {})
        print(f"\n  Processing Info:")
        print(f"    Model: {processing_info.get('primary_model', 'Unknown')}")
        print(f"    Escalated: {processing_info.get('escalated', False)}")
        print(f"    Type: {processing_info.get('extraction_type', 'Unknown')}")
        print(f"    Overall Confidence: {processing_info.get('confidence_score', 0):.2f}")
    
    # Quality Assessment
    print(f"\n🎯 QUALITY ASSESSMENT")
    print("=" * 30)
    
    if spacy_results and claude_results:
        # Count likely false positives (common issues)
        spacy_false_positives = count_likely_false_positives(spacy_persons)
        claude_false_positives = count_likely_false_positives(claude_people)
        
        print(f"Likely false positives:")
        print(f"  spaCy: {spacy_false_positives}/{len(spacy_persons)} ({spacy_false_positives/max(len(spacy_persons), 1)*100:.1f}%)")
        print(f"  Claude: {claude_false_positives}/{len(claude_people)} ({claude_false_positives/max(len(claude_people), 1)*100:.1f}%)")
        
        # Identify key political figures that should be captured
        expected_figures = identify_expected_political_figures(newsletter_data.get('text', ''))
        print(f"\nExpected key figures: {expected_figures}")
        
        spacy_captured = count_captured_figures(spacy_persons, expected_figures)
        claude_captured = count_captured_figures(claude_people, expected_figures)
        
        print(f"Captured key figures:")
        print(f"  spaCy: {spacy_captured}/{len(expected_figures)} ({spacy_captured/max(len(expected_figures), 1)*100:.1f}%)")
        print(f"  Claude: {claude_captured}/{len(expected_figures)} ({claude_captured/max(len(expected_figures), 1)*100:.1f}%)")


def count_likely_false_positives(entities):
    """Count likely false positive entities (journalists, staff, etc.)"""
    false_positive_indicators = [
        'calen', 'cassandra', 'benjamin', 'alec',  # Newsletter authors
        'jessica piper', 'katherine', 'jennifer',  # Likely journalists
        'francis chung', 'connor', 'mackenzie',    # More journalists
        'jordain carney', 'joe gould'              # More journalists
    ]
    
    false_positives = 0
    for entity in entities:
        name = entity.get('name', '').lower()
        if any(indicator in name for indicator in false_positive_indicators):
            false_positives += 1
        # Check for broken/malformed names
        if '[' in name or len(name.split()) == 1 and len(name) < 6:
            false_positives += 1
    
    return false_positives


def identify_expected_political_figures(text):
    """Identify key political figures that should definitely be captured."""
    expected_figures = []
    
    # Key figures that should be found in the sample newsletter
    key_political_figures = [
        'donald trump', 'trump',
        'chuck schumer', 'schumer', 
        'john thune', 'thune',
        'chris van hollen', 'van hollen',
        'jerry moran', 'moran',
        'amy klobuchar', 'klobuchar',
        'john kennedy', 'kennedy',
        'susan collins', 'collins',
        'lisa murkowski', 'murkowski'
    ]
    
    text_lower = text.lower()
    for figure in key_political_figures:
        if figure in text_lower:
            # Add the longer form name if found
            if figure in ['trump']:
                expected_figures.append('Donald Trump')
            elif figure in ['schumer']:
                expected_figures.append('Chuck Schumer')
            elif figure in ['thune']:
                expected_figures.append('John Thune')
            elif figure == figure:  # Full name already
                expected_figures.append(figure.title())
    
    return list(set(expected_figures))  # Remove duplicates


def count_captured_figures(entities, expected_figures):
    """Count how many expected figures were captured."""
    captured = 0
    entity_names = [entity.get('name', '').lower() for entity in entities]
    
    for expected in expected_figures:
        expected_lower = expected.lower()
        # Check if any entity name contains the expected figure
        if any(expected_lower in name for name in entity_names):
            captured += 1
    
    return captured


if __name__ == "__main__":
    compare_approaches()