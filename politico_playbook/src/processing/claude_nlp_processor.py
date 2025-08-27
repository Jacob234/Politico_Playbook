#!/usr/bin/env python3
"""
Claude-Based Political Newsletter NLP Processor

High-accuracy political entity and relationship extraction using Claude 3.5 Haiku and Sonnet.
Two-tier system: Haiku for primary extraction, Sonnet for complex/uncertain cases.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import anthropic
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class EntityResult:
    """Represents an extracted political entity with confidence scoring."""
    name: str
    entity_type: str  # person, organization, location
    titles: List[str]
    party: Optional[str] = None
    state: Optional[str] = None
    confidence: float = 0.0
    context: str = ""
    start_pos: int = 0
    end_pos: int = 0


@dataclass
class RelationshipResult:
    """Represents an extracted political relationship."""
    subject: str
    predicate: str  # met_with, appointed, supports, etc.
    object: str
    context: str
    confidence: float = 0.0
    relationship_type: str = "interaction"  # interaction, appointment, policy_position


class ClaudeNLPProcessor:
    """
    High-accuracy political NLP processor using Claude models.
    
    Architecture:
    1. Primary extraction with Claude-3.5-Haiku (fast, cost-effective)
    2. Selective escalation to Claude-3.5-Sonnet for complex cases
    3. Confidence-based routing and validation
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude NLP processor.
        
        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Model configuration
        self.haiku_model = "claude-3-5-haiku-20241022"
        self.sonnet_model = "claude-3-5-sonnet-20241022"
        
        # Processing thresholds
        self.confidence_threshold = 0.85  # Below this triggers Sonnet escalation
        self.max_tokens_haiku = 20000
        self.max_tokens_sonnet = 30000
        
        # Cost tracking
        self.total_cost = 0.0
        self.haiku_calls = 0
        self.sonnet_calls = 0
    
    def process_newsletter(self, newsletter_data: Dict) -> Dict:
        """
        Process a single newsletter with Claude-based NLP extraction.
        
        Args:
            newsletter_data: Dictionary containing newsletter text and metadata
            
        Returns:
            Enhanced newsletter data with Claude NLP results
        """
        text = newsletter_data.get('text', '')
        if not text:
            return newsletter_data
        
        print(f"Processing newsletter: {newsletter_data.get('subject_line', 'Unknown')}")
        
        # Stage 1: Primary extraction with Haiku
        primary_results = self._haiku_extract(text)
        
        # Stage 2: Selective Sonnet escalation for uncertain cases
        if self._needs_escalation(primary_results):
            print(f"  → Escalating to Sonnet for enhanced accuracy")
            enhanced_results = self._sonnet_enhance(text, primary_results)
            final_results = self._merge_results(primary_results, enhanced_results)
        else:
            final_results = primary_results
        
        # Add Claude NLP results to newsletter
        newsletter_data['claude_nlp_results'] = {
            'people': self._format_people(final_results.get('people', [])),
            'relationships': self._format_relationships(final_results.get('relationships', [])),
            'organizations': self._format_organizations(final_results.get('organizations', [])),
            'stories_and_topics': self._format_stories(final_results.get('stories_and_topics', [])),
            'context': final_results.get('context', {}),
            'processing_info': {
                'timestamp': datetime.now().isoformat(),
                'primary_model': self.haiku_model,
                'escalated': self._needs_escalation(primary_results),
                'escalation_model': self.sonnet_model if self._needs_escalation(primary_results) else None,
                'confidence_score': final_results.get('overall_confidence', 0.0),
                'extraction_type': 'comprehensive'
            }
        }
        
        return newsletter_data
    
    def _haiku_extract(self, text: str) -> Dict:
        """Extract entities and relationships using Claude-3.5-Haiku."""
        
        prompt = self._create_haiku_prompt(text)
        
        try:
            message = self.client.messages.create(
                model=self.haiku_model,
                max_tokens=self.max_tokens_haiku,
                temperature=0.1,  # Low temperature for consistent extraction
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            self.haiku_calls += 1
            self.total_cost += 0.01  # Approximate cost tracking
            
            # Parse Claude's response
            response_text = message.content[0].text
            return self._parse_claude_response(response_text)
            
        except Exception as e:
            print(f"Error in Haiku extraction: {e}")
            return {'entities': [], 'relationships': [], 'context': {}, 'overall_confidence': 0.0}
    
    def _sonnet_enhance(self, text: str, primary_results: Dict) -> Dict:
        """Enhance uncertain entities using Claude-3.5-Sonnet."""
        
        prompt = self._create_sonnet_prompt(text, primary_results)
        
        try:
            message = self.client.messages.create(
                model=self.sonnet_model,
                max_tokens=self.max_tokens_sonnet,
                temperature=0.1,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }]
            )
            
            self.sonnet_calls += 1
            self.total_cost += 0.03  # Approximate cost tracking
            
            response_text = message.content[0].text
            return self._parse_claude_response(response_text)
            
        except Exception as e:
            print(f"Error in Sonnet enhancement: {e}")
            return primary_results
    
    def _create_haiku_prompt(self, text: str) -> str:
        """Create comprehensive prompt for extracting ALL people and information."""
        
        return f"""You are an expert political intelligence analyst. Extract ALL people mentioned in this political newsletter and comprehensively categorize them with their roles, affiliations, and what they reported on or were involved in.

EXTRACT ALL PEOPLE INCLUDING:
- Political officials (senators, representatives, cabinet members, governors, mayors)
- Journalists and reporters (with what they reported on)
- Government staffers and advisors (with their roles)
- Lobbyists and political operatives (with their activities)
- Private citizens mentioned in political context
- Former officials still politically relevant

FOR EACH PERSON PROVIDE IF AVAILABLE:
- Full name and current role/title
- Organization/employer (Politico, government agency, lobbying firm, etc.)
- Political party affiliation (if applicable)
- State/jurisdiction (if applicable) 
- What they reported on, said, or were involved in
- Their relationships and interactions with others

EXTRACT RELATIONSHIPS INCLUDING:
- Meetings and conversations
- Reporting relationships (who reported what about whom)
- Policy positions and statements
- Professional movements (hirings, departures)
- Social and professional connections

TEXT TO ANALYZE:
{text}  

REQUIRED JSON FORMAT:
{{
  "people": [
    {{
      "name": "Jessica Piper",
      "category": "journalist",
      "employer": "Politico",
      "role": "Reporter",
      "expertise": "campaign finance",
      "reported_on": ["Musk donations to GOP"],
      "context": "Jessica Piper reports that Musk's donations were enough...",
      "confidence": 0.95
    }},
    {{
      "name": "Chuck Schumer", 
      "category": "political_official",
      "employer": "U.S. Senate",
      "role": "Minority Leader",
      "party": "Democratic",
      "state": "NY",
      "involved_in": ["budget negotiations", "nominee confirmations"],
      "context": "Senate Minority Leader Chuck Schumer is negotiating...",
      "confidence": 0.95
    }},
    {{
      "name": "Jordan Ebert",
      "category": "political_staff", 
      "employer": "Mastercard",
      "role": "Director of U.S. Government Affairs",
      "previous_role": "Banking counsel at Senate Banking",
      "activity": "career move from government to private sector",
      "context": "Jordan Ebert has joined Mastercard as director...",
      "confidence": 0.90
    }}
  ],
  "relationships": [
    {{
      "subject": "Jessica Piper",
      "predicate": "reported_on",
      "object": "Musk GOP donations", 
      "context": "Jessica Piper reports that Musk's donations...",
      "confidence": 0.9,
      "type": "reporting"
    }},
    {{
      "subject": "John Thune",
      "predicate": "met_with",
      "object": "Donald Trump",
      "context": "Thune met with Trump Thursday to update him...",
      "confidence": 0.9,
      "type": "meeting"
    }}
  ],
  "organizations": [
    {{
      "name": "Mastercard",
      "type": "private_company",
      "activity": "hiring government affairs director",
      "context": "Jordan Ebert has joined Mastercard...",
      "confidence": 0.95
    }}
  ],
  "stories_and_topics": [
    {{
      "topic": "GOP super PAC donations",
      "key_figures": ["Musk", "Jessica Piper"],
      "details": "Musk became largest individual donor to House and Senate GOP super PACs",
      "reporter": "Jessica Piper",
      "confidence": 0.95
    }},
    {{
      "topic": "Senate confirmation negotiations", 
      "key_figures": ["Thune", "Schumer", "Trump"],
      "details": "Ongoing negotiations over Trump nominee confirmations",
      "confidence": 0.95
    }}
  ],
  "overall_confidence": 0.90
}}

Extract ALL people and information now:"""
    
    def _create_sonnet_prompt(self, text: str, primary_results: Dict) -> str:
        """Create enhanced prompt for Sonnet to expand and verify comprehensive information."""
        
        uncertain_people = [p for p in primary_results.get('people', []) 
                           if p.get('confidence', 0) < self.confidence_threshold]
        
        return f"""You are an expert political intelligence analyst with deep knowledge of current political figures, journalists, and government operations.

The primary analysis identified these people that need verification and enhancement:
{json.dumps(uncertain_people, indent=2) if uncertain_people else "No uncertain people found"}

Please analyze the FULL newsletter text and provide comprehensive extraction:

1. Verify and enhance ALL people mentioned with complete information
2. Add any missed people (officials, journalists, staffers, private sector)
3. Identify all reporting relationships (who reported what)
4. Extract all professional movements and activities
5. Capture all policy topics and storylines

FULL NEWSLETTER TEXT:
{text}

Be comprehensive - extract every person, story, and relationship mentioned.

REQUIRED JSON FORMAT:
{{
  "people": [
    {{
      "name": "Full Name",
      "category": "political_official|journalist|staff|lobbyist|private_citizen",
      "employer": "Organization/Company",
      "role": "Current Title/Position",
      "party": "Party affiliation if applicable",
      "state": "State if applicable",
      "expertise": "Area of expertise",
      "reported_on": ["Topics they reported on"],
      "involved_in": ["Activities/issues they're involved in"],
      "activity": "What they did/said in this newsletter",
      "context": "Supporting text from newsletter",
      "confidence": 0.95
    }}
  ],
  "relationships": [
    {{
      "subject": "Person 1",
      "predicate": "reported_on|met_with|appointed|hired|said_about", 
      "object": "Person 2 or Topic",
      "context": "Supporting text",
      "confidence": 0.9,
      "type": "reporting|meeting|appointment|hiring|statement"
    }}
  ],
  "organizations": [
    {{
      "name": "Organization Name",
      "type": "government|media|lobbying|private_company|political",
      "activity": "What they did in this newsletter",
      "people_involved": ["List of people"],
      "context": "Supporting text",
      "confidence": 0.95
    }}
  ],
  "stories_and_topics": [
    {{
      "topic": "Story/Policy Topic", 
      "key_figures": ["People involved"],
      "details": "Detailed description",
      "reporter": "Who reported this",
      "significance": "Why this matters",
      "context": "Supporting text",
      "confidence": 0.95
    }}
  ],
  "overall_confidence": 0.95
}}

Provide your comprehensive enhanced analysis:"""
    
    def _parse_claude_response(self, response: str) -> Dict:
        """Parse Claude's JSON response into structured data."""
        try:
            # Extract JSON from response (handle cases where Claude adds explanatory text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                print("Warning: Could not find JSON in Claude response")
                return {'entities': [], 'relationships': [], 'context': {}, 'overall_confidence': 0.0}
                
        except json.JSONDecodeError as e:
            print(f"Warning: JSON parsing error: {e}")
            print(f"Response text: {response[:500]}...")
            return {'entities': [], 'relationships': [], 'context': {}, 'overall_confidence': 0.0}
    
    def _needs_escalation(self, results: Dict) -> bool:
        """Determine if results need Sonnet escalation based on confidence."""
        overall_confidence = results.get('overall_confidence', 0.0)
        
        # Check for low-confidence people (new comprehensive format)
        people = results.get('people', [])
        uncertain_people = [p for p in people if p.get('confidence', 0) < self.confidence_threshold]
        
        # Also check legacy entities format for backward compatibility
        entities = results.get('entities', [])
        uncertain_entities = [e for e in entities if e.get('confidence', 0) < self.confidence_threshold]
        
        total_uncertain = len(uncertain_people) + len(uncertain_entities)
        total_people = len(people) + len(entities)
        
        # Escalate if overall confidence is low, multiple uncertain people, or too many people (suggests errors)
        return (overall_confidence < self.confidence_threshold or 
                total_uncertain > 3 or 
                total_people > 25)  # More lenient since we want comprehensive extraction
    
    def _merge_results(self, primary: Dict, enhanced: Dict) -> Dict:
        """Merge primary and enhanced results, prioritizing enhanced (higher confidence) versions."""
        merged = {
            'people': [],
            'relationships': [],
            'organizations': [],
            'stories_and_topics': [],
            'context': enhanced.get('context', primary.get('context', {})),
            'overall_confidence': enhanced.get('overall_confidence', primary.get('overall_confidence', 0.0))
        }
        
        # Prioritize enhanced results (from Sonnet) over primary (from Haiku)
        # Enhanced results are more accurate and comprehensive
        
        # Use enhanced people if available, otherwise primary
        if enhanced.get('people'):
            merged['people'] = enhanced.get('people', [])
        else:
            merged['people'] = primary.get('people', [])
            # Also include legacy entities format for backward compatibility
            for entity in primary.get('entities', []):
                person_record = {
                    'name': entity.get('name', ''),
                    'category': 'political_official',  # Legacy entities were political officials
                    'role': ', '.join(entity.get('titles', [])),
                    'party': entity.get('party'),
                    'state': entity.get('state'),
                    'context': entity.get('context', ''),
                    'confidence': entity.get('confidence', 0.0)
                }
                merged['people'].append(person_record)
        
        # Merge relationships (both sources)
        merged['relationships'].extend(enhanced.get('relationships', []))
        merged['relationships'].extend(primary.get('relationships', []))
        
        # Add enhanced-only fields
        merged['organizations'] = enhanced.get('organizations', [])
        merged['stories_and_topics'] = enhanced.get('stories_and_topics', [])
        
        return merged
    
    def _format_people(self, people: List[Dict]) -> List[Dict]:
        """Format people for consistent comprehensive output structure."""
        formatted = []
        for person in people:
            formatted.append({
                'name': person.get('name', ''),
                'category': person.get('category', 'unknown'),
                'employer': person.get('employer'),
                'role': person.get('role'),
                'party': person.get('party'),
                'state': person.get('state'),
                'expertise': person.get('expertise'),
                'reported_on': person.get('reported_on', []),
                'involved_in': person.get('involved_in', []),
                'activity': person.get('activity'),
                'previous_role': person.get('previous_role'),
                'confidence': person.get('confidence', 0.0),
                'context': person.get('context', '')[:300] + ('...' if len(person.get('context', '')) > 300 else '')
            })
        return formatted
    
    def _format_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Format relationships for consistent output structure."""
        formatted = []
        for rel in relationships:
            formatted.append({
                'subject': rel.get('subject', ''),
                'predicate': rel.get('predicate', ''),
                'object': rel.get('object', ''),
                'context': rel.get('context', '')[:300] + ('...' if len(rel.get('context', '')) > 300 else ''),
                'confidence': rel.get('confidence', 0.0),
                'type': rel.get('type', 'interaction')
            })
        return formatted
    
    def _format_organizations(self, organizations: List[Dict]) -> List[Dict]:
        """Format organizations for consistent output structure."""
        formatted = []
        for org in organizations:
            formatted.append({
                'name': org.get('name', ''),
                'type': org.get('type', 'unknown'),
                'activity': org.get('activity', ''),
                'people_involved': org.get('people_involved', []),
                'confidence': org.get('confidence', 0.0),
                'context': org.get('context', '')[:300] + ('...' if len(org.get('context', '')) > 300 else '')
            })
        return formatted
    
    def _format_stories(self, stories: List[Dict]) -> List[Dict]:
        """Format stories and topics for consistent output structure."""
        formatted = []
        for story in stories:
            formatted.append({
                'topic': story.get('topic', ''),
                'key_figures': story.get('key_figures', []),
                'details': story.get('details', ''),
                'reporter': story.get('reporter'),
                'significance': story.get('significance'),
                'confidence': story.get('confidence', 0.0),
                'context': story.get('context', '')[:400] + ('...' if len(story.get('context', '')) > 400 else '')
            })
        return formatted
    
    def get_cost_summary(self) -> Dict:
        """Get processing cost summary."""
        return {
            'total_estimated_cost': self.total_cost,
            'haiku_calls': self.haiku_calls,
            'sonnet_calls': self.sonnet_calls,
            'escalation_rate': self.sonnet_calls / max(self.haiku_calls, 1) * 100
        }


def process_newsletter_batch(input_dir: Path, output_dir: Path, max_newsletters: Optional[int] = None):
    """
    Process a batch of newsletters with Claude NLP.
    
    Args:
        input_dir: Directory containing JSON newsletters
        output_dir: Directory to save enhanced newsletters
        max_newsletters: Maximum number to process (None for all)
    """
    processor = ClaudeNLPProcessor()
    
    # Find newsletter files
    json_files = list(input_dir.glob("*.json"))
    if max_newsletters:
        json_files = json_files[:max_newsletters]
    
    print(f"🔍 Processing {len(json_files)} newsletters with Claude NLP")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    processed = 0
    errors = []
    
    for json_file in json_files:
        try:
            # Load newsletter
            with open(json_file, 'r', encoding='utf-8') as f:
                newsletter_data = json.load(f)
            
            # Process with Claude
            enhanced_data = processor.process_newsletter(newsletter_data)
            
            # Save enhanced version
            output_file = output_dir / f"claude_{json_file.name}"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
            
            processed += 1
            print(f"  ✅ {json_file.name} → {output_file.name}")
            
        except Exception as e:
            error_msg = f"Error processing {json_file.name}: {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")
    
    # Summary
    print(f"\n📊 PROCESSING SUMMARY")
    print(f"Successfully processed: {processed}/{len(json_files)} newsletters")
    print(f"Cost summary: {processor.get_cost_summary()}")
    
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    return processed, errors


if __name__ == "__main__":
    """Test the Claude NLP processor on collected newsletter data."""
    
    # Configuration
    base_dir = Path(__file__).parent.parent.parent
    input_dir = base_dir / "data" / "structured"
    output_dir = base_dir / "data" / "structured" / "claude_enhanced"
    
    print("🤖 Claude Political Newsletter NLP Processor")
    print("=" * 60)
    
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Please set your Anthropic API key:")
        print("export ANTHROPIC_API_KEY=your_api_key_here")
        exit(1)
    
    # Process newsletters
    try:
        process_newsletter_batch(input_dir, output_dir, max_newsletters=3)  # Start with 3 for testing
        print("\n✅ Claude NLP processing completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()