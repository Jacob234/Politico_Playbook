#!/usr/bin/env python3
"""
Stage 3 of 4-Stage Political Newsletter Processing Pipeline: Database Normalizer

Transforms enhanced structure from Stage 2 into database-ready objects with temporal context.
Handles entity deduplication, standardization, and cross-newsletter resolution.

Pipeline Stage 3: Enhanced Structure → Database Cleaned Data
Input: Comprehensive entities, relationships, organizations from Stage 2  
Output: Normalized, deduplicated, database-ready objects with temporal context
"""

import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib


@dataclass
class NormalizedPerson:
    """Database-ready person entity with temporal context."""
    canonical_name: str  # Standardized name
    alternative_names: List[str]  # Name variations found
    category: str
    current_employer: Optional[str]
    current_role: Optional[str]
    party_affiliation: Optional[str]
    state: Optional[str]
    expertise_areas: List[str]
    first_mentioned: str  # ISO date
    last_mentioned: str   # ISO date
    mention_count: int
    confidence_average: float
    entity_id: str  # Unique identifier for database
    newsletter_appearances: List[Dict]  # Track which newsletters mention this person


@dataclass
class NormalizedRelationship:
    """Database-ready relationship with temporal context."""
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    relationship_type: str
    first_observed: str  # ISO date
    last_observed: str   # ISO date
    observation_count: int
    confidence_average: float
    relationship_id: str  # Unique identifier
    contexts: List[Dict]  # Supporting evidence from newsletters


@dataclass
class NormalizedOrganization:
    """Database-ready organization with temporal context."""
    canonical_name: str
    alternative_names: List[str]
    organization_type: str
    primary_activity: str
    associated_people: List[str]  # Entity IDs
    first_mentioned: str
    last_mentioned: str
    mention_count: int
    confidence_average: float
    organization_id: str
    newsletter_appearances: List[Dict]


@dataclass
class NormalizedStory:
    """Database-ready story/topic with temporal context."""
    canonical_topic: str
    alternative_titles: List[str]
    key_figures: List[str]  # Entity IDs
    story_category: str  # policy, scandal, election, appointment, etc.
    first_reported: str
    last_updated: str
    report_count: int
    significance_score: float
    story_id: str
    timeline: List[Dict]  # Chronological developments


class DatabaseNormalizer:
    """
    Stage 3 processor: Normalize and prepare entities for database storage.
    
    Key functions:
    1. Entity deduplication across newsletters
    2. Name standardization and alias management
    3. Temporal tracking (first/last seen, mention counts)
    4. Cross-newsletter entity resolution
    5. Database-ready object generation
    """
    
    def __init__(self):
        """Initialize the database normalizer."""
        
        # Entity tracking across newsletters
        self.person_registry = {}  # canonical_name -> NormalizedPerson
        self.organization_registry = {}  # canonical_name -> NormalizedOrganization
        self.relationship_registry = {}  # relationship_key -> NormalizedRelationship
        self.story_registry = {}  # canonical_topic -> NormalizedStory
        
        # Name resolution mappings
        self.name_aliases = defaultdict(set)  # alternative_name -> canonical_name
        self.entity_id_map = {}  # entity_id -> canonical_name
        
        # Processing statistics
        self.processing_stats = {
            'newsletters_processed': 0,
            'entities_normalized': 0,
            'duplicates_merged': 0,
            'relationships_normalized': 0
        }
        
    def process_newsletter(self, newsletter_data: Dict) -> Dict:
        """
        Stage 3: Process newsletter from Enhanced Structure to Database Cleaned Data.
        
        Args:
            newsletter_data: Newsletter with claude_nlp_results from Stage 2
            
        Returns:
            Newsletter with normalized, database-ready entities
        """
        if 'claude_nlp_results' not in newsletter_data:
            print("⚠️ No Stage 2 results found. Skipping Stage 3 processing.")
            return newsletter_data
        
        newsletter_date = self._parse_newsletter_date(newsletter_data.get('date'))
        newsletter_id = newsletter_data.get('file_name', 'unknown')
        
        print(f"🗃️ Stage 3: Normalizing entities from {newsletter_id}")
        
        # Extract Stage 2 results
        stage2_results = newsletter_data['claude_nlp_results']
        
        # Normalize each entity type
        normalized_people = self._normalize_people(
            stage2_results.get('people', []), newsletter_date, newsletter_id
        )
        
        normalized_relationships = self._normalize_relationships(
            stage2_results.get('relationships', []), newsletter_date, newsletter_id
        )
        
        normalized_organizations = self._normalize_organizations(
            stage2_results.get('organizations', []), newsletter_date, newsletter_id
        )
        
        normalized_stories = self._normalize_stories(
            stage2_results.get('stories_and_topics', []), newsletter_date, newsletter_id
        )
        
        # Create database-ready structure
        newsletter_data['database_normalized_results'] = {
            'people': normalized_people,
            'relationships': normalized_relationships, 
            'organizations': normalized_organizations,
            'stories_and_topics': normalized_stories,
            'processing_info': {
                'timestamp': datetime.now().isoformat(),
                'stage': 'database_cleaned_data',
                'newsletter_date': newsletter_date.isoformat(),
                'newsletter_id': newsletter_id,
                'entities_normalized': len(normalized_people),
                'ready_for_stage_4': True
            }
        }
        
        self.processing_stats['newsletters_processed'] += 1
        
        return newsletter_data
    
    def _parse_newsletter_date(self, date_str: str) -> date:
        """Parse newsletter date from various formats."""
        if not date_str:
            return date.today()
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '')).date()
        except (ValueError, AttributeError):
            pass
        
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
        
        print(f"⚠️ Could not parse date: {date_str}. Using today's date.")
        return date.today()
    
    def _normalize_people(self, people: List[Dict], newsletter_date: date, newsletter_id: str) -> List[Dict]:
        """Normalize and deduplicate people entities."""
        normalized = []
        
        for person in people:
            name = person.get('name', '').strip()
            if not name:
                continue
                
            # Resolve canonical name and handle aliases
            canonical_name = self._resolve_canonical_name(name)
            
            # Get or create normalized person
            if canonical_name in self.person_registry:
                norm_person = self.person_registry[canonical_name]
                self._update_person_temporal_data(norm_person, person, newsletter_date, newsletter_id)
            else:
                norm_person = self._create_normalized_person(
                    person, canonical_name, newsletter_date, newsletter_id
                )
                self.person_registry[canonical_name] = norm_person
            
            normalized.append(asdict(norm_person))
            
        return normalized
    
    def _resolve_canonical_name(self, name: str) -> str:
        """Resolve name variants to canonical form."""
        # Clean and standardize name
        clean_name = self._clean_name(name)
        
        # Check if this is already a known alias
        if clean_name in self.name_aliases:
            return list(self.name_aliases[clean_name])[0]  # Return canonical name
        
        # Check for similar existing names (fuzzy matching)
        canonical_name = self._find_similar_name(clean_name)
        
        if canonical_name:
            # Add as alias
            self.name_aliases[clean_name].add(canonical_name)
            return canonical_name
        else:
            # New canonical name
            self.name_aliases[clean_name].add(clean_name)
            return clean_name
    
    def _clean_name(self, name: str) -> str:
        """Clean and standardize name format."""
        # Remove titles and honorifics
        name = re.sub(r'^(Sen\.|Rep\.|Dr\.|Mr\.|Ms\.|Mrs\.|President|Secretary)\s+', '', name, flags=re.IGNORECASE)
        
        # Remove party affiliations in parentheses
        name = re.sub(r'\s*\([^)]*\)$', '', name)
        
        # Standardize spacing and capitalization
        name = ' '.join(name.split())  # Normalize whitespace
        name = name.title()  # Title case
        
        # Handle common name variations
        name = re.sub(r'\bJr\.?$', 'Jr.', name)
        name = re.sub(r'\bSr\.?$', 'Sr.', name)
        name = re.sub(r'\bIII$', 'III', name)
        
        return name
    
    def _find_similar_name(self, clean_name: str) -> Optional[str]:
        """Find similar existing canonical names using fuzzy matching."""
        # Simple fuzzy matching for now - can be enhanced with libraries like fuzzywuzzy
        
        # Exact match first
        for canonical in self.person_registry.keys():
            if clean_name == canonical:
                return canonical
        
        # Check for obvious variations (last name + first initial)
        name_parts = clean_name.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]
            first_initial = name_parts[0][0] if name_parts[0] else ''
            
            for canonical in self.person_registry.keys():
                canonical_parts = canonical.split()
                if (len(canonical_parts) >= 2 and 
                    canonical_parts[-1] == last_name and
                    canonical_parts[0].startswith(first_initial)):
                    return canonical
        
        return None
    
    def _create_normalized_person(self, person: Dict, canonical_name: str, 
                                newsletter_date: date, newsletter_id: str) -> NormalizedPerson:
        """Create new normalized person entity."""
        entity_id = self._generate_entity_id('person', canonical_name)
        
        return NormalizedPerson(
            canonical_name=canonical_name,
            alternative_names=[person.get('name', '')],
            category=person.get('category', 'unknown'),
            current_employer=person.get('employer'),
            current_role=person.get('role'),
            party_affiliation=person.get('party'),
            state=person.get('state'),
            expertise_areas=person.get('expertise', '').split(',') if person.get('expertise') else [],
            first_mentioned=newsletter_date.isoformat(),
            last_mentioned=newsletter_date.isoformat(),
            mention_count=1,
            confidence_average=person.get('confidence', 0.0),
            entity_id=entity_id,
            newsletter_appearances=[{
                'newsletter_id': newsletter_id,
                'date': newsletter_date.isoformat(),
                'context': person.get('context', ''),
                'activity': person.get('activity', ''),
                'confidence': person.get('confidence', 0.0)
            }]
        )
    
    def _update_person_temporal_data(self, norm_person: NormalizedPerson, person: Dict, 
                                   newsletter_date: date, newsletter_id: str) -> None:
        """Update existing person with new temporal data."""
        # Add name variation if new
        person_name = person.get('name', '').strip()
        if person_name and person_name not in norm_person.alternative_names:
            norm_person.alternative_names.append(person_name)
        
        # Update temporal data
        norm_person.last_mentioned = newsletter_date.isoformat()
        norm_person.mention_count += 1
        
        # Update confidence average
        new_confidence = person.get('confidence', 0.0)
        norm_person.confidence_average = (
            (norm_person.confidence_average * (norm_person.mention_count - 1) + new_confidence) / 
            norm_person.mention_count
        )
        
        # Update current role/employer if more recent or higher confidence
        if (person.get('employer') and 
            (not norm_person.current_employer or new_confidence > 0.8)):
            norm_person.current_employer = person.get('employer')
            
        if (person.get('role') and 
            (not norm_person.current_role or new_confidence > 0.8)):
            norm_person.current_role = person.get('role')
        
        # Add newsletter appearance
        norm_person.newsletter_appearances.append({
            'newsletter_id': newsletter_id,
            'date': newsletter_date.isoformat(),
            'context': person.get('context', ''),
            'activity': person.get('activity', ''),
            'confidence': new_confidence
        })
    
    def _normalize_relationships(self, relationships: List[Dict], newsletter_date: date, 
                               newsletter_id: str) -> List[Dict]:
        """Normalize and deduplicate relationships."""
        normalized = []
        
        for rel in relationships:
            subject = rel.get('subject', '').strip()
            predicate = rel.get('predicate', '').strip()
            obj = rel.get('object', '').strip()
            
            if not (subject and predicate and obj):
                continue
            
            # Resolve entity IDs for subject and object
            subject_canonical = self._resolve_canonical_name(subject)
            object_canonical = self._resolve_canonical_name(obj)
            
            subject_id = self._generate_entity_id('person', subject_canonical)
            object_id = self._generate_entity_id('person', object_canonical)
            
            # Create relationship key for deduplication
            rel_key = f"{subject_id}:{predicate}:{object_id}"
            
            if rel_key in self.relationship_registry:
                norm_rel = self.relationship_registry[rel_key]
                self._update_relationship_temporal_data(norm_rel, rel, newsletter_date, newsletter_id)
            else:
                norm_rel = self._create_normalized_relationship(
                    rel, subject_id, object_id, newsletter_date, newsletter_id
                )
                self.relationship_registry[rel_key] = norm_rel
            
            normalized.append(asdict(norm_rel))
        
        return normalized
    
    def _create_normalized_relationship(self, rel: Dict, subject_id: str, object_id: str,
                                      newsletter_date: date, newsletter_id: str) -> NormalizedRelationship:
        """Create new normalized relationship."""
        rel_id = self._generate_entity_id('relationship', f"{subject_id}:{rel.get('predicate', '')}:{object_id}")
        
        return NormalizedRelationship(
            subject_entity_id=subject_id,
            predicate=rel.get('predicate', ''),
            object_entity_id=object_id,
            relationship_type=rel.get('type', 'interaction'),
            first_observed=newsletter_date.isoformat(),
            last_observed=newsletter_date.isoformat(),
            observation_count=1,
            confidence_average=rel.get('confidence', 0.0),
            relationship_id=rel_id,
            contexts=[{
                'newsletter_id': newsletter_id,
                'date': newsletter_date.isoformat(),
                'context': rel.get('context', ''),
                'confidence': rel.get('confidence', 0.0)
            }]
        )
    
    def _update_relationship_temporal_data(self, norm_rel: NormalizedRelationship, rel: Dict,
                                         newsletter_date: date, newsletter_id: str) -> None:
        """Update existing relationship with new temporal data."""
        norm_rel.last_observed = newsletter_date.isoformat()
        norm_rel.observation_count += 1
        
        # Update confidence average
        new_confidence = rel.get('confidence', 0.0)
        norm_rel.confidence_average = (
            (norm_rel.confidence_average * (norm_rel.observation_count - 1) + new_confidence) /
            norm_rel.observation_count
        )
        
        # Add context
        norm_rel.contexts.append({
            'newsletter_id': newsletter_id,
            'date': newsletter_date.isoformat(),
            'context': rel.get('context', ''),
            'confidence': new_confidence
        })
    
    def _normalize_organizations(self, organizations: List[Dict], newsletter_date: date, 
                               newsletter_id: str) -> List[Dict]:
        """Normalize and deduplicate organizations.""" 
        normalized = []
        
        for org in organizations:
            name = org.get('name', '').strip()
            if not name:
                continue
            
            canonical_name = self._resolve_canonical_organization_name(name)
            
            if canonical_name in self.organization_registry:
                norm_org = self.organization_registry[canonical_name]
                self._update_organization_temporal_data(norm_org, org, newsletter_date, newsletter_id)
            else:
                norm_org = self._create_normalized_organization(
                    org, canonical_name, newsletter_date, newsletter_id
                )
                self.organization_registry[canonical_name] = norm_org
            
            normalized.append(asdict(norm_org))
        
        return normalized
    
    def _resolve_canonical_organization_name(self, name: str) -> str:
        """Resolve organization name variants to canonical form."""
        # Simple canonicalization for now
        clean_name = name.strip()
        
        # Check for exact matches first
        for canonical in self.organization_registry.keys():
            if clean_name.lower() == canonical.lower():
                return canonical
        
        # Return as-is if no match (new organization)
        return clean_name
    
    def _create_normalized_organization(self, org: Dict, canonical_name: str,
                                      newsletter_date: date, newsletter_id: str) -> NormalizedOrganization:
        """Create new normalized organization."""
        org_id = self._generate_entity_id('organization', canonical_name)
        
        return NormalizedOrganization(
            canonical_name=canonical_name,
            alternative_names=[org.get('name', '')],
            organization_type=org.get('type', 'unknown'),
            primary_activity=org.get('activity', ''),
            associated_people=org.get('people_involved', []),
            first_mentioned=newsletter_date.isoformat(),
            last_mentioned=newsletter_date.isoformat(),
            mention_count=1,
            confidence_average=org.get('confidence', 0.0),
            organization_id=org_id,
            newsletter_appearances=[{
                'newsletter_id': newsletter_id,
                'date': newsletter_date.isoformat(),
                'context': org.get('context', ''),
                'activity': org.get('activity', ''),
                'confidence': org.get('confidence', 0.0)
            }]
        )
    
    def _update_organization_temporal_data(self, norm_org: NormalizedOrganization, org: Dict,
                                         newsletter_date: date, newsletter_id: str) -> None:
        """Update existing organization with new temporal data."""
        norm_org.last_mentioned = newsletter_date.isoformat()
        norm_org.mention_count += 1
        
        # Update confidence average
        new_confidence = org.get('confidence', 0.0)
        norm_org.confidence_average = (
            (norm_org.confidence_average * (norm_org.mention_count - 1) + new_confidence) /
            norm_org.mention_count
        )
        
        # Add newsletter appearance
        norm_org.newsletter_appearances.append({
            'newsletter_id': newsletter_id,
            'date': newsletter_date.isoformat(),
            'context': org.get('context', ''),
            'activity': org.get('activity', ''),
            'confidence': new_confidence
        })
    
    def _normalize_stories(self, stories: List[Dict], newsletter_date: date,
                         newsletter_id: str) -> List[Dict]:
        """Normalize and deduplicate stories/topics."""
        normalized = []
        
        for story in stories:
            topic = story.get('topic', '').strip()
            if not topic:
                continue
            
            canonical_topic = self._resolve_canonical_story_topic(topic)
            
            if canonical_topic in self.story_registry:
                norm_story = self.story_registry[canonical_topic]
                self._update_story_temporal_data(norm_story, story, newsletter_date, newsletter_id)
            else:
                norm_story = self._create_normalized_story(
                    story, canonical_topic, newsletter_date, newsletter_id
                )
                self.story_registry[canonical_topic] = norm_story
            
            normalized.append(asdict(norm_story))
        
        return normalized
    
    def _resolve_canonical_story_topic(self, topic: str) -> str:
        """Resolve story topic variants to canonical form."""
        # Simple canonicalization for now
        clean_topic = topic.strip()
        
        # Check for exact matches first
        for canonical in self.story_registry.keys():
            if clean_topic.lower() == canonical.lower():
                return canonical
        
        return clean_topic
    
    def _create_normalized_story(self, story: Dict, canonical_topic: str,
                               newsletter_date: date, newsletter_id: str) -> NormalizedStory:
        """Create new normalized story."""
        story_id = self._generate_entity_id('story', canonical_topic)
        
        return NormalizedStory(
            canonical_topic=canonical_topic,
            alternative_titles=[story.get('topic', '')],
            key_figures=story.get('key_figures', []),
            story_category=self._classify_story_category(story),
            first_reported=newsletter_date.isoformat(),
            last_updated=newsletter_date.isoformat(),
            report_count=1,
            significance_score=story.get('confidence', 0.0),
            story_id=story_id,
            timeline=[{
                'date': newsletter_date.isoformat(),
                'newsletter_id': newsletter_id,
                'details': story.get('details', ''),
                'reporter': story.get('reporter', ''),
                'significance': story.get('significance', '')
            }]
        )
    
    def _update_story_temporal_data(self, norm_story: NormalizedStory, story: Dict,
                                  newsletter_date: date, newsletter_id: str) -> None:
        """Update existing story with new temporal data."""
        norm_story.last_updated = newsletter_date.isoformat()
        norm_story.report_count += 1
        
        # Update significance score (average)
        new_significance = story.get('confidence', 0.0)
        norm_story.significance_score = (
            (norm_story.significance_score * (norm_story.report_count - 1) + new_significance) /
            norm_story.report_count
        )
        
        # Add to timeline
        norm_story.timeline.append({
            'date': newsletter_date.isoformat(),
            'newsletter_id': newsletter_id,
            'details': story.get('details', ''),
            'reporter': story.get('reporter', ''),
            'significance': story.get('significance', '')
        })
    
    def _classify_story_category(self, story: Dict) -> str:
        """Classify story category based on content."""
        topic = story.get('topic', '').lower()
        details = story.get('details', '').lower()
        
        # Simple keyword-based classification
        if any(word in topic + details for word in ['election', 'campaign', 'primary', 'vote']):
            return 'election'
        elif any(word in topic + details for word in ['nominee', 'confirmation', 'appointment']):
            return 'appointment'
        elif any(word in topic + details for word in ['funding', 'budget', 'appropriation', 'spending']):
            return 'budget'
        elif any(word in topic + details for word in ['policy', 'bill', 'legislation', 'law']):
            return 'policy'
        elif any(word in topic + details for word in ['scandal', 'investigation', 'ethics']):
            return 'scandal'
        else:
            return 'general'
    
    def _generate_entity_id(self, entity_type: str, canonical_name: str) -> str:
        """Generate unique entity ID for database."""
        # Create hash-based ID for consistency
        id_string = f"{entity_type}:{canonical_name}"
        hash_obj = hashlib.md5(id_string.encode())
        return f"{entity_type}_{hash_obj.hexdigest()[:12]}"
    
    def get_processing_summary(self) -> Dict:
        """Get processing statistics summary."""
        return {
            'newsletters_processed': self.processing_stats['newsletters_processed'],
            'unique_people': len(self.person_registry),
            'unique_organizations': len(self.organization_registry),
            'unique_relationships': len(self.relationship_registry),
            'unique_stories': len(self.story_registry),
            'name_aliases_tracked': len(self.name_aliases),
            'entities_normalized': self.processing_stats['entities_normalized']
        }
    
    def export_entity_registry(self, output_dir: Path) -> Dict[str, str]:
        """Export entity registries for database import."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        files_created = {}
        
        # Export people registry
        people_file = output_dir / "normalized_people_registry.json"
        with open(people_file, 'w', encoding='utf-8') as f:
            people_data = {name: asdict(person) for name, person in self.person_registry.items()}
            json.dump(people_data, f, indent=2, ensure_ascii=False)
        files_created['people'] = str(people_file)
        
        # Export organizations registry
        orgs_file = output_dir / "normalized_organizations_registry.json"
        with open(orgs_file, 'w', encoding='utf-8') as f:
            orgs_data = {name: asdict(org) for name, org in self.organization_registry.items()}
            json.dump(orgs_data, f, indent=2, ensure_ascii=False)
        files_created['organizations'] = str(orgs_file)
        
        # Export relationships registry
        rels_file = output_dir / "normalized_relationships_registry.json"
        with open(rels_file, 'w', encoding='utf-8') as f:
            rels_data = {key: asdict(rel) for key, rel in self.relationship_registry.items()}
            json.dump(rels_data, f, indent=2, ensure_ascii=False)
        files_created['relationships'] = str(rels_file)
        
        # Export stories registry
        stories_file = output_dir / "normalized_stories_registry.json"
        with open(stories_file, 'w', encoding='utf-8') as f:
            stories_data = {topic: asdict(story) for topic, story in self.story_registry.items()}
            json.dump(stories_data, f, indent=2, ensure_ascii=False)
        files_created['stories'] = str(stories_file)
        
        return files_created


def process_newsletter_batch_stage3(input_dir: Path, output_dir: Path, 
                                   max_newsletters: Optional[int] = None) -> Tuple[int, List[str]]:
    """
    Process a batch of newsletters through Stage 3 normalization.
    
    Args:
        input_dir: Directory containing Stage 2 enhanced newsletters
        output_dir: Directory to save Stage 3 normalized newsletters
        max_newsletters: Maximum number to process
        
    Returns:
        Tuple of (processed_count, errors)
    """
    normalizer = DatabaseNormalizer()
    
    # Find enhanced newsletter files
    json_files = list(input_dir.glob("claude_*.json"))  # Stage 2 files
    if max_newsletters:
        json_files = json_files[:max_newsletters]
    
    print(f"🗃️ Stage 3: Processing {len(json_files)} newsletters for database normalization")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    processed = 0
    errors = []
    
    for json_file in json_files:
        try:
            # Load Stage 2 enhanced newsletter
            with open(json_file, 'r', encoding='utf-8') as f:
                newsletter_data = json.load(f)
            
            # Process with Stage 3 normalizer
            normalized_data = normalizer.process_newsletter(newsletter_data)
            
            # Save Stage 3 normalized version
            output_file = output_dir / f"normalized_{json_file.name}"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(normalized_data, f, indent=2, ensure_ascii=False)
            
            processed += 1
            print(f"  ✅ {json_file.name} → {output_file.name}")
            
        except Exception as e:
            error_msg = f"Error processing {json_file.name}: {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")
    
    # Export entity registries
    registry_files = normalizer.export_entity_registry(output_dir / "registries")
    
    # Summary
    print(f"\n🗃️ STAGE 3 PROCESSING SUMMARY")
    print(f"Successfully processed: {processed}/{len(json_files)} newsletters")
    
    summary = normalizer.get_processing_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print(f"\n📊 Entity registries exported:")
    for entity_type, file_path in registry_files.items():
        print(f"  {entity_type}: {file_path}")
    
    if errors:
        print(f"\nErrors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    return processed, errors


if __name__ == "__main__":
    """Test Stage 3 database normalization on enhanced newsletters."""
    
    # Configuration
    base_dir = Path(__file__).parent.parent.parent
    input_dir = base_dir / "data" / "structured" / "claude_enhanced"  # Stage 2 output
    output_dir = base_dir / "data" / "structured" / "database_normalized"  # Stage 3 output
    
    print("🗃️ Political Newsletter Database Normalizer - Stage 3")
    print("=" * 65)
    
    # Process newsletters
    try:
        process_newsletter_batch_stage3(input_dir, output_dir, max_newsletters=5)  # Start with 5 for testing
        print("\n✅ Stage 3 database normalization completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()