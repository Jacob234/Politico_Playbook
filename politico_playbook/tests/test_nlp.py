#!/usr/bin/env python3
"""
Test script for NLP processor on collected newsletter data.
"""

import json
import os
from pathlib import Path
from src.processing.nlp_processor import NewsletterNLPProcessor


def test_nlp_on_sample_newsletter():
    """Test the NLP processor on a single newsletter."""
    
    # Initialize NLP processor
    processor = NewsletterNLPProcessor()
    
    # Load a sample newsletter
    data_dir = Path(__file__).parent / "data" / "structured"
    sample_file = data_dir / "2025-08-01_085105_email.json"
    
    print(f"Testing NLP processor on: {sample_file}")
    
    # Load newsletter data
    with open(sample_file, 'r', encoding='utf-8') as f:
        newsletter_data = json.load(f)
    
    print(f"Newsletter subject: {newsletter_data.get('subject_line', 'N/A')}")
    print(f"Authors: {newsletter_data.get('authors', [])}")
    print(f"Text length: {len(newsletter_data.get('text', ''))} characters")
    
    # Process with NLP
    print("\n🔍 Running NLP extraction...")
    processed_data = processor.process_newsletter(newsletter_data)
    
    # Display results
    nlp_results = processed_data.get('nlp_results', {})
    
    print("\n📊 NLP RESULTS SUMMARY")
    print("=" * 50)
    
    # Entities
    entities = nlp_results.get('entities', {})
    print(f"\n👥 PERSONS ({len(entities.get('persons', []))} found):")
    for person in entities.get('persons', [])[:5]:  # Show first 5
        titles = ', '.join(person.get('titles', []))
        party = person.get('party', 'Unknown')
        state = person.get('state', 'Unknown')
        print(f"  - {person['name']} ({titles}) [{party}-{state}] (conf: {person.get('confidence', 0):.1f})")
    
    print(f"\n🏛️  ORGANIZATIONS ({len(entities.get('organizations', []))} found):")
    for org in entities.get('organizations', [])[:5]:  # Show first 5
        print(f"  - {org['name']} ({org.get('type', 'unknown')}) (conf: {org.get('confidence', 0):.1f})")
    
    print(f"\n📍 LOCATIONS ({len(entities.get('locations', []))} found):")
    for loc in entities.get('locations', [])[:5]:  # Show first 5
        print(f"  - {loc['name']} ({loc.get('type', 'unknown')}) (conf: {loc.get('confidence', 0):.1f})")
    
    print(f"\n📅 EVENTS ({len(entities.get('events', []))} found):")
    for event in entities.get('events', [])[:3]:  # Show first 3
        print(f"  - {event.get('type', 'unknown')}: {event.get('text', 'N/A')} (conf: {event.get('confidence', 0):.1f})")
    
    # Relationships
    relationships = nlp_results.get('relationships', [])
    print(f"\n🤝 RELATIONSHIPS ({len(relationships)} found):")
    for rel in relationships[:5]:  # Show first 5
        print(f"  - {rel.get('subject', 'N/A')} → {rel.get('predicate', 'N/A')} → {rel.get('object', 'N/A')} (conf: {rel.get('confidence', 0):.1f})")
    
    # Context analysis
    context = nlp_results.get('context', {})
    print(f"\n🎯 CONTEXT ANALYSIS:")
    print(f"  Topics: {', '.join(context.get('main_topics', []))}")
    print(f"  Sentiment: {context.get('sentiment', 'neutral')}")
    print(f"  Key Figures: {', '.join(context.get('key_figures', [])[:3])}")
    print(f"  Events: {context.get('political_events', {})}")
    print(f"  Urgency: {', '.join(context.get('urgency_indicators', []))}")
    
    # Save enhanced results
    output_file = data_dir / "nlp_enhanced" / f"{sample_file.stem}_nlp.json"
    os.makedirs(output_file.parent, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Enhanced newsletter saved to: {output_file}")
    
    return processed_data


def test_multiple_newsletters():
    """Test NLP processor on multiple newsletters."""
    
    processor = NewsletterNLPProcessor()
    data_dir = Path(__file__).parent / "data" / "structured"
    
    # Process first 3 newsletters
    json_files = sorted(data_dir.glob("*.json"))[:3]
    
    print(f"\n🔄 Processing {len(json_files)} newsletters...")
    
    all_results = []
    
    for json_file in json_files:
        print(f"\nProcessing: {json_file.name}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            newsletter_data = json.load(f)
        
        processed_data = processor.process_newsletter(newsletter_data)
        all_results.append(processed_data)
        
        # Quick summary
        nlp_results = processed_data.get('nlp_results', {})
        entities = nlp_results.get('entities', {})
        relationships = nlp_results.get('relationships', [])
        
        print(f"  - Persons: {len(entities.get('persons', []))}")
        print(f"  - Organizations: {len(entities.get('organizations', []))}")  
        print(f"  - Relationships: {len(relationships)}")
    
    # Aggregate analysis
    print(f"\n📈 AGGREGATE ANALYSIS:")
    
    all_persons = set()
    all_orgs = set()
    all_relationships = []
    
    for result in all_results:
        nlp_results = result.get('nlp_results', {})
        entities = nlp_results.get('entities', {})
        
        for person in entities.get('persons', []):
            all_persons.add(person['name'])
        
        for org in entities.get('organizations', []):
            all_orgs.add(org['name'])
        
        all_relationships.extend(nlp_results.get('relationships', []))
    
    print(f"  Total unique persons: {len(all_persons)}")
    print(f"  Total unique organizations: {len(all_orgs)}")
    print(f"  Total relationships: {len(all_relationships)}")
    
    # Most mentioned persons
    person_counts = {}
    for result in all_results:
        nlp_results = result.get('nlp_results', {})
        entities = nlp_results.get('entities', {})
        for person in entities.get('persons', []):
            name = person['name']
            person_counts[name] = person_counts.get(name, 0) + 1
    
    print(f"\n👑 Most mentioned persons:")
    for name, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {name}: {count} mentions")


if __name__ == "__main__":
    print("🚀 Testing Political Newsletter NLP Processor")
    print("=" * 60)
    
    # Test single newsletter
    try:
        test_nlp_on_sample_newsletter()
    except Exception as e:
        print(f"❌ Error in single newsletter test: {e}")
        import traceback
        traceback.print_exc()
    
    # Test multiple newsletters
    try:
        test_multiple_newsletters()
    except Exception as e:
        print(f"❌ Error in multiple newsletter test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ NLP testing completed!")