def _create_haiku_prompt(self, text: str) -> str:
    """Create comprehensive prompt for extracting ALL people and information."""
    
    return f"""Extract ALL people from this political newsletter. Most newsletters have 15-30+ people.

TEXT: {text}

Return ONLY valid JSON:
{{
  "people": [
    {{"name": "Full Name", "category": "political_official|journalist|staff|other", "role": "Position", "party": "Party", "employer": "Organization", "activity": "What they did", "context": "Quote", "confidence": 0.9}}
  ],
  "relationships": [
    {{"subject": "Person1", "predicate": "met_with|reported_on", "object": "Person2", "context": "Context", "confidence": 0.9, "type": "meeting|reporting"}}
  ],
  "organizations": [
    {{"name": "Name", "type": "government|media|private", "activity": "What they did", "confidence": 0.9}}
  ],
  "stories_and_topics": [
    {{"topic": "Topic Name", "key_figures": ["Names"], "details": "Details", "confidence": 0.9}}
  ],
  "overall_confidence": 0.9
}}"""