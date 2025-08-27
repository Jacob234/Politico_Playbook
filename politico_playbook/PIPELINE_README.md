# 4-Stage Political Newsletter Processing Pipeline

A comprehensive system for transforming raw political newsletters into structured data, enhanced entities, normalized database records, and temporal analysis ready for graph visualization and time series analysis.

## Architecture Overview

```
Raw HTML → Structured → Enhanced Structure → Database Ready → Graph/Time Series
   (1)         (2)            (3)               (4)
```

### Stage 1: Raw HTML → Structured

- **Input**: Raw HTML email files, EML files
- **Output**: Clean JSON with metadata and text
- **Purpose**: Extract basic newsletter structure and clean text
- **Tool**: `email_extractor.py` (existing)

### Stage 2: Structured → Enhanced Structure

- **Input**: Structured JSON newsletters
- **Output**: JSON with comprehensive entity extraction
- **Purpose**: Extract 25-30+ political entities per newsletter
- **Tool**: `claude_nlp_processor.py` (redesigned for single Sonnet 4 model)
- **Key Features**:
  - Single Claude Sonnet 4 model (no two-tier complexity)
  - Comprehensive extraction of officials, journalists, staff, private sector
  - High-accuracy political intelligence gathering

### Stage 3: Enhanced Structure → Database Cleaned Data

- **Input**: Enhanced JSON with extracted entities
- **Output**: Normalized, deduplicated entities with temporal context
- **Purpose**: Prepare database-ready objects with entity resolution
- **Tool**: `database_normalizer.py` (new)
- **Key Features**:
  - Entity deduplication across newsletters
  - Temporal tracking (first/last seen, mention counts)
  - Cross-newsletter entity resolution
  - Canonical name resolution and alias management

### Stage 4: Database Cleaned Data → Graph/Time Series Ready

- **Input**: Normalized entities with temporal context
- **Output**: Graph nodes/edges, time series data, political trends
- **Purpose**: Generate network analysis and temporal intelligence
- **Tool**: `temporal_analyzer.py` (new)
- **Key Features**:
  - Political network graph construction
  - Influence and centrality metrics
  - Political trend identification
  - Time series data for visualization

## Quick Start

### 1. Setup Environment

```bash
# Set API key
export ANTHROPIC_API_KEY="your_api_key_here"

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Complete Pipeline

```bash
cd src
python pipeline_orchestrator.py
```

### 3. Run Individual Stages

```bash
# Stage 2 only (Claude NLP)
python processing/claude_nlp_processor.py

# Stage 3 only (Database Normalization) 
python processing/database_normalizer.py

# Stage 4 only (Temporal Analysis)
python processing/temporal_analyzer.py
```

## Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional overrides
export CLAUDE_MODEL="claude-sonnet-4-20250514"
export CLAUDE_TEMPERATURE="0.3"
export MAX_NEWSLETTERS="10"
export LOG_LEVEL="INFO"
```

### Configuration File

```bash
# Create default config
python src/config/pipeline_config.py create-default my_config.json

# Use custom config
python src/pipeline_orchestrator.py --config my_config.json
```

## Output Structure

```
data/
├── structured/                    # Stage 1 output
│   ├── 2025-08-01_email.json
│   └── ...
├── structured/claude_enhanced/    # Stage 2 output  
│   ├── claude_2025-08-01_email.json
│   └── ...
├── structured/database_normalized/ # Stage 3 output
│   ├── normalized_claude_2025-08-01_email.json
│   ├── registries/
│   │   ├── normalized_people_registry.json
│   │   ├── normalized_organizations_registry.json
│   │   └── ...
│   └── ...
└── analysis/temporal_results/     # Stage 4 output
    ├── temporal_analysis_complete.json
    ├── political_network_graph.json
    ├── political_time_series.csv
    ├── political_trends.json
    └── influence_networks.json
```

## Key Improvements

### From Previous Architecture

- ❌ **Old**: Complex two-tier Haiku→Sonnet system with escalation logic
- ✅ **New**: Single Sonnet 4 model for consistent high-quality extraction
- ❌ **Old**: Only 3-5 entities extracted per newsletter
- ✅ **New**: 25-30+ entities extracted comprehensively
- ❌ **Old**: No temporal context or entity tracking
- ✅ **New**: Full temporal analysis with entity evolution tracking
- ❌ **Old**: Limited to basic entity extraction
- ✅ **New**: Complete pipeline to graph-ready political intelligence

### Performance Metrics

- **Stage 2**: ~30s per newsletter, 25-30+ entities extracted
- **Stage 3**: ~5s per newsletter for normalization
- **Stage 4**: ~60s for complete temporal analysis of batch
- **Total Cost**: ~$0.03 per newsletter (Sonnet 4 pricing)

## Entity Types Extracted

### Political Officials (15+ per newsletter)

- Presidents, Senators, Representatives
- Cabinet members, Administrators
- State and local officials
- Nominees and appointees

### Journalists & Media (8+ per newsletter)

- Newsletter authors and bylines
- Quoted reporters and sources
- Media organization representatives

### Staff & Advisors (5+ per newsletter)

- Government staff and aides
- Campaign staff and consultants
- Spokespeople and communications staff

### Private Sector (3+ per newsletter)

- Lobbyists and government affairs professionals
- Business leaders and executives
- Think tank researchers and analysts

## Analysis Outputs

### Political Network Graph

- **Nodes**: Political entities with influence scores
- **Edges**: Relationships with interaction strengths
- **Metrics**: Centrality, clustering, community detection
- **Format**: JSON for Gephi/Cytoscape, visualization libraries

### Time Series Analysis

- **Entity Activity**: Tracking political activity over time
- **Influence Trends**: Rising/declining political figures
- **Relationship Evolution**: How connections change
- **Format**: CSV for analysis, JSON for applications

### Political Intelligence

- **Trend Identification**: Emerging political patterns
- **Influence Networks**: Key political communities
- **Story Tracking**: Policy issues over time
- **Significance Scoring**: Impact assessment

## Troubleshooting

### Common Issues

**Stage 2: Low entity extraction**

- Check prompt complexity in `claude_nlp_processor.py`
- Verify Claude Sonnet 4 model access
- Review confidence thresholds

**Stage 3: Entity resolution problems**

- Check name fuzzy matching settings
- Review canonical name resolution logic
- Verify entity deduplication

**Stage 4: Graph analysis errors**

- Check for minimum node/edge thresholds
- Verify NetworkX compatibility
- Review memory limits for large graphs

### Performance Optimization

**Cost Optimization**

- Use batch processing for Stage 2
- Set appropriate `max_newsletters_per_batch`
- Monitor cost tracking in configuration

**Speed Optimization**

- Enable parallel processing where appropriate
- Use caching for entity lookups in Stage 3
- Optimize graph algorithms for large networks

**Memory Optimization**

- Clear caches between stages
- Use streaming processing for large datasets
- Set appropriate memory limits

## Development

### Adding New Entity Types

1. Update extraction prompts in `claude_nlp_processor.py`
2. Add normalization logic in `database_normalizer.py`
3. Include in temporal analysis in `temporal_analyzer.py`
4. Update configuration schema

### Extending Analysis

1. Add new metrics in `temporal_analyzer.py`
2. Create new export formats as needed
3. Update configuration options
4. Document new outputs

### Testing

```bash
# Test individual stages
python -m pytest tests/test_claude_nlp.py
python -m pytest tests/test_normalizer.py
python -m pytest tests/test_temporal.py

# Test complete pipeline
python -m pytest tests/test_pipeline.py
```

## API Reference

### Pipeline Orchestrator

```python
from src.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig

config = PipelineConfig(max_newsletters_per_batch=10)
orchestrator = PipelineOrchestrator(config)
results = orchestrator.run_complete_pipeline()
```

### Configuration Management

```python
from src.config.pipeline_config import ConfigurationManager

manager = ConfigurationManager("my_config.json")
config = manager.get_config()
```

### Individual Stage Processing

```python
from src.processing.claude_nlp_processor import ClaudeNLPProcessor
from src.processing.database_normalizer import DatabaseNormalizer  
from src.processing.temporal_analyzer import TemporalAnalyzer

# Stage 2
processor = ClaudeNLPProcessor()
enhanced_data = processor.process_newsletter(newsletter_data)

# Stage 3  
normalizer = DatabaseNormalizer()
normalized_data = normalizer.process_newsletter(enhanced_data)

# Stage 4
analyzer = TemporalAnalyzer() 
analysis_results = analyzer.process_newsletter_batch(input_dir)
```

## Contributing

1. Follow the 4-stage architecture principles
2. Maintain configuration compatibility
3. Add comprehensive error handling
4. Include performance metrics
5. Update documentation

## License

[Your chosen license]

---

**Questions?** Check the troubleshooting section or open an issue with detailed logs and configuration.
