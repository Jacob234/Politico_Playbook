"""
Newsletter NLP Processor

Main NLP pipeline for extracting entities, relationships, and political intelligence
from Politico newsletter text content.
"""

import re
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span


class NewsletterNLPProcessor:
    """
    Main NLP processing pipeline for political newsletters.
    
    Extracts:
    - Person entities with titles and roles
    - Organization entities (government, political, private)
    - Relationships and interactions between entities
    - Personnel changes (appointments, resignations)
    - Policy positions and legislative actions
    """
    
    def __init__(self, model_name: str = "en_core_web_lg", lexicon_path: Optional[str] = None):
        """
        Initialize the NLP processor.
        
        Args:
            model_name: spaCy model to use
            lexicon_path: Path to political lexicon JSON file
        """
        self.nlp = spacy.load(model_name)
        self.matcher = Matcher(self.nlp.vocab)
        
        # Load political lexicon
        if lexicon_path is None:
            lexicon_path = Path(__file__).parent.parent.parent / "config" / "lexicon.json"
        self.lexicon = self._load_lexicon(lexicon_path)
        
        # Initialize entity extractors
        self.entity_extractor = EntityExtractor(self.nlp, self.lexicon)
        self.relationship_extractor = RelationshipExtractor(self.nlp, self.lexicon)
        self.context_analyzer = PoliticalContextAnalyzer(self.nlp, self.lexicon)
        
        # Setup custom patterns
        self._setup_custom_patterns()
    
    def _load_lexicon(self, lexicon_path: Path) -> Dict:
        """Load the political lexicon from JSON file."""
        try:
            with open(lexicon_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Lexicon file not found at {lexicon_path}, using empty lexicon")
            return {}
    
    def _setup_custom_patterns(self):
        """Setup custom spaCy patterns for political entities."""
        # Title patterns for people
        title_patterns = [
            [{"LOWER": "senator"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "rep"}, {"LOWER": "."}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "representative"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "president"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "vice"}, {"LOWER": "president"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "secretary"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "chair"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "chairman"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "chairwoman"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "majority"}, {"LOWER": "leader"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "minority"}, {"LOWER": "leader"}, {"ENT_TYPE": "PERSON"}],
            [{"LOWER": "speaker"}, {"ENT_TYPE": "PERSON"}],
        ]
        
        for i, pattern in enumerate(title_patterns):
            self.matcher.add(f"POLITICAL_TITLE_{i}", [pattern])
    
    def process_newsletter(self, newsletter_data: Dict) -> Dict:
        """
        Process a single newsletter and extract all NLP data.
        
        Args:
            newsletter_data: Dictionary with newsletter content and metadata
            
        Returns:
            Enhanced dictionary with NLP extraction results
        """
        text = newsletter_data.get('text', '')
        if not text:
            return newsletter_data
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(doc)
        
        # Extract relationships
        relationships = self.relationship_extractor.extract_relationships(doc, entities)
        
        # Analyze political context
        context = self.context_analyzer.analyze_context(doc, entities, relationships)
        
        # Add NLP results to newsletter data
        newsletter_data['nlp_results'] = {
            'entities': entities,
            'relationships': relationships,
            'context': context,
            'processing_timestamp': datetime.now().isoformat(),
            'model_version': self.nlp.meta.get('version', 'unknown')
        }
        
        return newsletter_data


class EntityExtractor:
    """Extracts and classifies political entities from text."""
    
    def __init__(self, nlp, lexicon: Dict):
        self.nlp = nlp
        self.lexicon = lexicon
        
        # Political titles and roles
        self.political_titles = self._get_political_titles()
        self.government_orgs = self._get_government_organizations()
    
    def _get_political_titles(self) -> Set[str]:
        """Get set of political titles from lexicon."""
        titles = set()
        
        # From lexicon roles
        if 'roles' in self.lexicon:
            titles.update(self.lexicon['roles'].keys())
        
        # Common political titles
        common_titles = {
            'senator', 'representative', 'congressman', 'congresswoman',
            'president', 'vice president', 'secretary', 'chair', 'chairman', 
            'chairwoman', 'majority leader', 'minority leader', 'speaker',
            'whip', 'ranking member', 'governor', 'mayor', 'attorney general',
            'chief of staff', 'press secretary', 'director'
        }
        titles.update(common_titles)
        
        return titles
    
    def _get_government_organizations(self) -> Set[str]:
        """Get set of government organizations from lexicon."""
        orgs = set()
        
        # From lexicon organizations
        if 'organizations' in self.lexicon:
            for org_data in self.lexicon['organizations'].values():
                orgs.add(org_data.get('name', '').lower())
                orgs.update([acronym.lower() for acronym in org_data.get('acronyms', [])])
        
        # From lexicon acronyms
        if 'acronyms' in self.lexicon:
            for acronym_data in self.lexicon['acronyms'].values():
                if acronym_data.get('entity_type') == 'organization':
                    orgs.add(acronym_data.get('expansion', '').lower())
                    orgs.add(acronym_data.get('acronym', '').lower())
        
        return orgs
    
    def extract_entities(self, doc: Doc) -> Dict[str, List[Dict]]:
        """
        Extract all entity types from the document.
        
        Args:
            doc: spaCy processed document
            
        Returns:
            Dictionary with entity lists by type
        """
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'events': [],
            'policies': []
        }
        
        # Extract persons with political context
        entities['persons'] = self._extract_persons(doc)
        
        # Extract organizations
        entities['organizations'] = self._extract_organizations(doc)
        
        # Extract locations
        entities['locations'] = self._extract_locations(doc)
        
        # Extract political events
        entities['events'] = self._extract_events(doc)
        
        # Extract policy mentions
        entities['policies'] = self._extract_policies(doc)
        
        return entities
    
    def _extract_persons(self, doc: Doc) -> List[Dict]:
        """Extract person entities with political roles and titles."""
        persons = []
        seen_names = set()
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                if name.lower() in seen_names or len(name) < 3:
                    continue
                
                # Look for titles in surrounding context
                title, party, state = self._extract_person_context(doc, ent)
                
                person_data = {
                    'name': name,
                    'titles': title if title else [],
                    'party': party,
                    'state': state,
                    'start_char': ent.start_char,
                    'end_char': ent.end_char,
                    'confidence': 0.9 if title else 0.7
                }
                
                persons.append(person_data)
                seen_names.add(name.lower())
        
        return persons
    
    def _extract_person_context(self, doc: Doc, person_ent: Span) -> Tuple[List[str], Optional[str], Optional[str]]:
        """Extract title, party, and state for a person entity."""
        titles = []
        party = None
        state = None
        
        # Look in surrounding 10 tokens before and after
        start_idx = max(0, person_ent.start - 10)
        end_idx = min(len(doc), person_ent.end + 10)
        context = doc[start_idx:end_idx]
        
        context_text = context.text.lower()
        
        # Extract titles
        for title in self.political_titles:
            if title in context_text:
                titles.append(title.title())
        
        # Extract party affiliation
        party_patterns = [
            r'\(([DR])-([A-Z]{2})\)',  # (D-NY) or (R-TX)
            r'democrat(?:ic)?',
            r'republican'
        ]
        
        for pattern in party_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                if match.group(0).startswith('('):
                    party = 'Democratic' if match.group(1) == 'D' else 'Republican'
                    state = match.group(2)
                else:
                    party = 'Democratic' if 'democrat' in match.group(0) else 'Republican'
                break
        
        return titles, party, state
    
    def _extract_organizations(self, doc: Doc) -> List[Dict]:
        """Extract organization entities."""
        organizations = []
        seen_orgs = set()
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                name = ent.text.strip()
                if name.lower() in seen_orgs or len(name) < 3:
                    continue
                
                org_type = self._classify_organization(name)
                
                org_data = {
                    'name': name,
                    'type': org_type,
                    'start_char': ent.start_char,
                    'end_char': ent.end_char,
                    'confidence': 0.8
                }
                
                organizations.append(org_data)
                seen_orgs.add(name.lower())
        
        return organizations
    
    def _classify_organization(self, org_name: str) -> str:
        """Classify organization type based on name and lexicon."""
        org_lower = org_name.lower()
        
        # Check against lexicon
        if org_lower in self.government_orgs:
            return 'government'
        
        # Pattern-based classification
        government_keywords = [
            'committee', 'department', 'agency', 'bureau', 'service',
            'administration', 'commission', 'board', 'office', 'court'
        ]
        
        political_keywords = [
            'party', 'democratic', 'republican', 'pac', 'campaign',
            'committee', 'caucus'
        ]
        
        for keyword in government_keywords:
            if keyword in org_lower:
                return 'government'
        
        for keyword in political_keywords:
            if keyword in org_lower:
                return 'political'
        
        return 'other'
    
    def _extract_locations(self, doc: Doc) -> List[Dict]:
        """Extract location entities relevant to political context."""
        locations = []
        seen_locations = set()
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                name = ent.text.strip()
                if name.lower() in seen_locations or len(name) < 3:
                    continue
                
                location_data = {
                    'name': name,
                    'type': ent.label_,
                    'start_char': ent.start_char,
                    'end_char': ent.end_char,
                    'confidence': 0.8
                }
                
                locations.append(location_data)
                seen_locations.add(name.lower())
        
        return locations
    
    def _extract_events(self, doc: Doc) -> List[Dict]:
        """Extract political events like meetings, hearings, votes."""
        events = []
        
        # Event keywords and patterns
        event_patterns = [
            (r'meeting\s+(?:with|between)', 'meeting'),
            (r'hearing\s+on', 'hearing'),
            (r'vote\s+on', 'vote'),
            (r'confirmation\s+of', 'confirmation'),
            (r'nomination\s+of', 'nomination'),
            (r'appointment\s+of', 'appointment'),
            (r'resignation\s+of', 'resignation')
        ]
        
        for pattern, event_type in event_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                event_data = {
                    'type': event_type,
                    'text': match.group(0),
                    'start_char': match.start(),
                    'end_char': match.end(),
                    'confidence': 0.7
                }
                events.append(event_data)
        
        return events
    
    def _extract_policies(self, doc: Doc) -> List[Dict]:
        """Extract policy and legislative mentions."""
        policies = []
        
        # Policy keywords and patterns
        policy_patterns = [
            (r'(?:bill|legislation|act|amendment)\s+[A-Z0-9-]+', 'legislation'),
            (r'(?:budget|spending|funding|appropriations)', 'fiscal'),
            (r'(?:tariff|trade|import|export)', 'trade'),
            (r'(?:healthcare|health\s+care|medicaid|medicare)', 'healthcare'),
            (r'(?:climate|environment|energy)', 'environment')
        ]
        
        for pattern, policy_type in policy_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                policy_data = {
                    'type': policy_type,
                    'text': match.group(0),
                    'start_char': match.start(),
                    'end_char': match.end(),
                    'confidence': 0.6
                }
                policies.append(policy_data)
        
        return policies


class RelationshipExtractor:
    """Extracts relationships and interactions between entities."""
    
    def __init__(self, nlp, lexicon: Dict):
        self.nlp = nlp
        self.lexicon = lexicon
    
    def extract_relationships(self, doc: Doc, entities: Dict) -> List[Dict]:
        """
        Extract relationships between entities.
        
        Args:
            doc: spaCy processed document
            entities: Previously extracted entities
            
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
        # Extract meeting relationships
        relationships.extend(self._extract_meetings(doc, entities))
        
        # Extract appointment/nomination relationships
        relationships.extend(self._extract_appointments(doc, entities))
        
        # Extract policy positions
        relationships.extend(self._extract_policy_positions(doc, entities))
        
        # Extract communication relationships
        relationships.extend(self._extract_communications(doc, entities))
        
        return relationships
    
    def _extract_meetings(self, doc: Doc, entities: Dict) -> List[Dict]:
        """Extract meeting relationships."""
        relationships = []
        
        meeting_patterns = [
            r'(\w+(?:\s+\w+)*?)\s+(?:met|meeting|meets)\s+with\s+(\w+(?:\s+\w+)*?)(?:\s|$|\.)',
            r'(\w+(?:\s+\w+)*?)\s+and\s+(\w+(?:\s+\w+)*?)\s+(?:met|meeting)(?:\s|$|\.)',
        ]
        
        for pattern in meeting_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                subject = match.group(1).strip()
                object_entity = match.group(2).strip() if len(match.groups()) > 1 else None
                
                if subject and object_entity:
                    relationship = {
                        'subject': subject,
                        'predicate': 'met_with',
                        'object': object_entity,
                        'context': match.group(0),
                        'start_char': match.start(),
                        'end_char': match.end(),
                        'confidence': 0.8
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_appointments(self, doc: Doc, entities: Dict) -> List[Dict]:
        """Extract appointment and nomination relationships."""
        relationships = []
        
        appointment_patterns = [
            r'(\w+(?:\s+\w+)*?)\s+(?:nominated|appointed|named)\s+(\w+(?:\s+\w+)*?)\s+(?:as|for|to)',
            r'(\w+(?:\s+\w+)*?)\s+(?:confirmed|approved)\s+(?:as|for|to)\s+(\w+(?:\s+\w+)*?)',
        ]
        
        for pattern in appointment_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                subject = match.group(1).strip()
                position = match.group(2).strip() if len(match.groups()) > 1 else None
                
                if subject and position:
                    relationship = {
                        'subject': subject,
                        'predicate': 'appointed_to',
                        'object': position,
                        'context': match.group(0),
                        'start_char': match.start(),
                        'end_char': match.end(),
                        'confidence': 0.9
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_policy_positions(self, doc: Doc, entities: Dict) -> List[Dict]:
        """Extract policy position relationships."""
        relationships = []
        
        position_patterns = [
            r'(\w+(?:\s+\w+)*?)\s+(?:supports|opposes|backs|endorses)\s+(\w+(?:\s+\w+)*?)(?:\s|$|\.)',
            r'(\w+(?:\s+\w+)*?)\s+(?:voted|votes)\s+(?:for|against)\s+(\w+(?:\s+\w+)*?)(?:\s|$|\.)',
        ]
        
        for pattern in position_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                subject = match.group(1).strip()
                policy = match.group(2).strip() if len(match.groups()) > 1 else None
                
                if subject and policy:
                    predicate = 'supports' if any(word in match.group(0).lower() 
                                                for word in ['supports', 'backs', 'endorses', 'for']) else 'opposes'
                    
                    relationship = {
                        'subject': subject,
                        'predicate': predicate,
                        'object': policy,
                        'context': match.group(0),
                        'start_char': match.start(),
                        'end_char': match.end(),
                        'confidence': 0.7
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_communications(self, doc: Doc, entities: Dict) -> List[Dict]:
        """Extract communication relationships."""
        relationships = []
        
        communication_patterns = [
            r'(\w+(?:\s+\w+)*?)\s+(?:told|said\s+to|wrote\s+to)\s+(\w+(?:\s+\w+)*?)(?:\s|$|\.)',
            r'(\w+(?:\s+\w+)*?)\s+and\s+(\w+(?:\s+\w+)*?)\s+(?:discussed|talked\s+about)(?:\s|$|\.)',
        ]
        
        for pattern in communication_patterns:
            for match in re.finditer(pattern, doc.text, re.IGNORECASE):
                subject = match.group(1).strip()
                object_entity = match.group(2).strip() if len(match.groups()) > 1 else None
                
                if subject and object_entity:
                    relationship = {
                        'subject': subject,
                        'predicate': 'communicated_with',
                        'object': object_entity,
                        'context': match.group(0),
                        'start_char': match.start(),
                        'end_char': match.end(),
                        'confidence': 0.6
                    }
                    relationships.append(relationship)
        
        return relationships


class PoliticalContextAnalyzer:
    """Analyzes political context and sentiment of extracted data."""
    
    def __init__(self, nlp, lexicon: Dict):
        self.nlp = nlp
        self.lexicon = lexicon
    
    def analyze_context(self, doc: Doc, entities: Dict, relationships: List[Dict]) -> Dict:
        """
        Analyze the political context of the newsletter.
        
        Args:
            doc: spaCy processed document
            entities: Extracted entities
            relationships: Extracted relationships
            
        Returns:
            Context analysis results
        """
        context = {
            'main_topics': self._identify_main_topics(doc, entities),
            'sentiment': self._analyze_sentiment(doc),
            'key_figures': self._identify_key_figures(entities, relationships),
            'political_events': self._categorize_events(entities.get('events', [])),
            'urgency_indicators': self._detect_urgency(doc)
        }
        
        return context
    
    def _identify_main_topics(self, doc: Doc, entities: Dict) -> List[str]:
        """Identify main political topics in the newsletter."""
        topics = []
        
        # Topic keywords
        topic_keywords = {
            'budget': ['budget', 'spending', 'appropriations', 'funding'],
            'nominations': ['nominee', 'confirmation', 'appointment'],
            'legislation': ['bill', 'vote', 'committee', 'markup'],
            'foreign_policy': ['international', 'foreign', 'diplomacy', 'trade'],
            'elections': ['campaign', 'election', 'polling', 'candidate']
        }
        
        doc_text = doc.text.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in doc_text for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _analyze_sentiment(self, doc: Doc) -> str:
        """Basic sentiment analysis of the newsletter."""
        # Simple keyword-based sentiment
        positive_words = ['success', 'agreement', 'progress', 'support', 'approval']
        negative_words = ['crisis', 'failure', 'oppose', 'controversy', 'scandal']
        
        doc_text = doc.text.lower()
        
        positive_count = sum(1 for word in positive_words if word in doc_text)
        negative_count = sum(1 for word in negative_words if word in doc_text)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _identify_key_figures(self, entities: Dict, relationships: List[Dict]) -> List[str]:
        """Identify the most important political figures mentioned."""
        person_mentions = {}
        
        # Count person mentions
        for person in entities.get('persons', []):
            name = person['name']
            person_mentions[name] = person_mentions.get(name, 0) + 1
        
        # Weight by relationship involvement
        for rel in relationships:
            subject = rel.get('subject', '')
            obj = rel.get('object', '')
            
            person_mentions[subject] = person_mentions.get(subject, 0) + 2
            person_mentions[obj] = person_mentions.get(obj, 0) + 1
        
        # Return top mentioned figures
        return sorted(person_mentions.keys(), key=person_mentions.get, reverse=True)[:5]
    
    def _categorize_events(self, events: List[Dict]) -> Dict[str, int]:
        """Categorize political events by type."""
        event_counts = {}
        
        for event in events:
            event_type = event.get('type', 'other')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return event_counts
    
    def _detect_urgency(self, doc: Doc) -> List[str]:
        """Detect urgency indicators in the text."""
        urgency_patterns = [
            'breaking', 'urgent', 'immediately', 'crisis', 'emergency',
            'deadline', 'last minute', 'rushed', 'pressure'
        ]
        
        doc_text = doc.text.lower()
        found_indicators = []
        
        for indicator in urgency_patterns:
            if indicator in doc_text:
                found_indicators.append(indicator)
        
        return found_indicators