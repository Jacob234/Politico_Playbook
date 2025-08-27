#!/usr/bin/env python3
"""
Configuration Management for 4-Stage Political Newsletter Processing Pipeline

Centralized configuration system supporting:
- Environment variables
- JSON configuration files  
- Runtime configuration updates
- Validation and defaults
- Stage-specific settings
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging


@dataclass
class Stage1Config:
    """Stage 1: Raw HTML → Structured configuration."""
    
    # Email extraction settings
    email_patterns: List[str] = field(default_factory=lambda: [
        "*.html", "*.eml", "*.msg"
    ])
    
    # Text cleaning
    remove_html_tags: bool = True
    normalize_whitespace: bool = True
    extract_metadata: bool = True
    
    # Output format
    output_format: str = "json"
    include_raw_html: bool = False


@dataclass  
class Stage2Config:
    """Stage 2: Structured → Enhanced Structure (Claude NLP) configuration."""
    
    # Model settings
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    max_tokens: int = 8192
    
    # Processing settings
    batch_size: int = 5
    retry_attempts: int = 3
    timeout_seconds: int = 300
    
    # Cost management
    max_cost_per_batch: float = 10.0  # USD
    cost_tracking_enabled: bool = True
    
    # Extraction settings
    min_entities_per_newsletter: int = 5
    min_confidence_threshold: float = 0.7
    extract_all_categories: bool = True
    
    # Rate limiting
    requests_per_minute: int = 60
    concurrent_requests: int = 3


@dataclass
class Stage3Config:
    """Stage 3: Enhanced Structure → Database Cleaned Data configuration."""
    
    # Entity normalization
    enable_name_fuzzy_matching: bool = True
    fuzzy_match_threshold: float = 0.85
    deduplicate_entities: bool = True
    
    # Temporal tracking
    track_entity_evolution: bool = True
    calculate_influence_scores: bool = True
    
    # Database preparation
    generate_entity_ids: bool = True
    export_registries: bool = True
    validate_relationships: bool = True
    
    # Performance settings
    batch_processing: bool = True
    cache_entity_lookups: bool = True


@dataclass
class Stage4Config:
    """Stage 4: Database Cleaned Data → Graph/Time Series Ready configuration."""
    
    # Graph analysis
    calculate_centrality_metrics: bool = True
    detect_communities: bool = True
    min_community_size: int = 3
    
    # Time series analysis
    generate_trends: bool = True
    min_trend_strength: float = 0.5
    trend_analysis_window_days: int = 30
    
    # Network analysis
    max_nodes_for_analysis: int = 1000
    include_temporal_snapshots: bool = True
    
    # Export formats
    export_gephi_format: bool = True
    export_csv_timeseries: bool = True
    export_json_complete: bool = True


@dataclass
class ProcessingLimits:
    """Processing limits and resource management."""
    
    max_newsletters_total: Optional[int] = None
    max_newsletters_per_stage: Optional[int] = None
    max_processing_time_minutes: int = 180  # 3 hours
    
    # Memory management
    max_memory_mb: int = 4096
    clear_cache_between_stages: bool = True
    
    # Parallel processing
    max_worker_threads: int = 4
    enable_multiprocessing: bool = False


@dataclass
class OutputConfig:
    """Output and export configuration."""
    
    # Directory structure
    base_output_dir: str = "data"
    structured_subdir: str = "structured"
    enhanced_subdir: str = "structured/claude_enhanced"  
    normalized_subdir: str = "structured/database_normalized"
    analysis_subdir: str = "analysis/temporal_results"
    
    # File naming
    use_timestamps_in_filenames: bool = True
    compress_large_files: bool = False
    
    # Reporting
    generate_summary_reports: bool = True
    include_performance_metrics: bool = True
    export_configuration_snapshots: bool = True
    
    # Cleanup
    cleanup_intermediate_files: bool = False
    archive_old_results: bool = False


@dataclass
class ErrorHandling:
    """Error handling and recovery configuration."""
    
    # Strategy
    continue_on_errors: bool = True
    max_errors_per_stage: int = 10
    retry_failed_items: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "pipeline.log"
    detailed_error_reports: bool = True
    
    # Recovery
    save_partial_results: bool = True
    enable_checkpoint_recovery: bool = True


@dataclass
class PipelineConfiguration:
    """Complete pipeline configuration."""
    
    # Configuration metadata
    config_version: str = "2.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = "4-Stage Political Newsletter Processing Pipeline Configuration"
    
    # Stage configurations
    stage1: Stage1Config = field(default_factory=Stage1Config)
    stage2: Stage2Config = field(default_factory=Stage2Config)
    stage3: Stage3Config = field(default_factory=Stage3Config)
    stage4: Stage4Config = field(default_factory=Stage4Config)
    
    # Global settings
    processing_limits: ProcessingLimits = field(default_factory=ProcessingLimits)
    output: OutputConfig = field(default_factory=OutputConfig)
    error_handling: ErrorHandling = field(default_factory=ErrorHandling)
    
    # API Configuration
    anthropic_api_key: Optional[str] = None
    
    # Environment
    environment: str = "development"  # development, testing, production


class ConfigurationManager:
    """
    Manages configuration loading, validation, and updates for the pipeline.
    
    Supports:
    - Environment variable overrides
    - JSON configuration files
    - Runtime configuration updates
    - Validation and error checking
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.config = PipelineConfiguration()
        self._setup_logging()
        
        # Load configuration from sources
        self._load_from_environment()
        if config_file and Path(config_file).exists():
            self._load_from_file(config_file)
        
        # Validate configuration
        self._validate_configuration()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.error_handling.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=self.config.error_handling.log_file
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        
        # API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            self.config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Stage 2 (Claude) settings
        if os.getenv("CLAUDE_MODEL"):
            self.config.stage2.model = os.getenv("CLAUDE_MODEL")
        
        if os.getenv("CLAUDE_TEMPERATURE"):
            self.config.stage2.temperature = float(os.getenv("CLAUDE_TEMPERATURE"))
        
        if os.getenv("CLAUDE_MAX_TOKENS"):
            self.config.stage2.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS"))
        
        # Processing limits
        if os.getenv("MAX_NEWSLETTERS"):
            self.config.processing_limits.max_newsletters_total = int(os.getenv("MAX_NEWSLETTERS"))
        
        if os.getenv("MAX_PROCESSING_TIME"):
            self.config.processing_limits.max_processing_time_minutes = int(os.getenv("MAX_PROCESSING_TIME"))
        
        # Output directories
        if os.getenv("OUTPUT_BASE_DIR"):
            self.config.output.base_output_dir = os.getenv("OUTPUT_BASE_DIR")
        
        # Error handling
        if os.getenv("LOG_LEVEL"):
            self.config.error_handling.log_level = os.getenv("LOG_LEVEL")
        
        if os.getenv("CONTINUE_ON_ERRORS"):
            self.config.error_handling.continue_on_errors = os.getenv("CONTINUE_ON_ERRORS").lower() == "true"
        
        # Environment
        if os.getenv("PIPELINE_ENV"):
            self.config.environment = os.getenv("PIPELINE_ENV")
    
    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Update configuration with file data
            self._update_config_from_dict(config_data)
            
            self.logger.info(f"Configuration loaded from {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from {config_file}: {e}")
            raise
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from dictionary data."""
        
        # Update stage configurations
        if "stage1" in config_data:
            self._update_dataclass_from_dict(self.config.stage1, config_data["stage1"])
        
        if "stage2" in config_data:
            self._update_dataclass_from_dict(self.config.stage2, config_data["stage2"])
        
        if "stage3" in config_data:
            self._update_dataclass_from_dict(self.config.stage3, config_data["stage3"])
        
        if "stage4" in config_data:
            self._update_dataclass_from_dict(self.config.stage4, config_data["stage4"])
        
        # Update global settings
        if "processing_limits" in config_data:
            self._update_dataclass_from_dict(self.config.processing_limits, config_data["processing_limits"])
        
        if "output" in config_data:
            self._update_dataclass_from_dict(self.config.output, config_data["output"])
        
        if "error_handling" in config_data:
            self._update_dataclass_from_dict(self.config.error_handling, config_data["error_handling"])
        
        # Update top-level settings
        if "anthropic_api_key" in config_data:
            self.config.anthropic_api_key = config_data["anthropic_api_key"]
        
        if "environment" in config_data:
            self.config.environment = config_data["environment"]
    
    def _update_dataclass_from_dict(self, dataclass_instance: Any, update_dict: Dict[str, Any]) -> None:
        """Update dataclass instance with dictionary values."""
        for key, value in update_dict.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)
    
    def _validate_configuration(self) -> None:
        """Validate configuration settings."""
        
        errors = []
        
        # Validate API key
        if not self.config.anthropic_api_key:
            errors.append("Anthropic API key is required")
        
        # Validate Stage 2 settings
        if self.config.stage2.temperature < 0 or self.config.stage2.temperature > 2:
            errors.append("Stage 2 temperature must be between 0 and 2")
        
        if self.config.stage2.max_tokens < 100 or self.config.stage2.max_tokens > 8192:
            errors.append("Stage 2 max_tokens must be between 100 and 8192")
        
        # Validate processing limits
        if self.config.processing_limits.max_processing_time_minutes < 1:
            errors.append("Processing time limit must be at least 1 minute")
        
        # Validate directories exist or can be created
        base_dir = Path(self.config.output.base_output_dir)
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create base output directory: {e}")
        
        if errors:
            error_msg = "Configuration validation failed:\\n" + "\\n".join(f"  - {error}" for error in errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info("Configuration validation passed")
    
    def get_config(self) -> PipelineConfiguration:
        """Get the current configuration."""
        return self.config
    
    def save_config(self, output_file: str) -> None:
        """Save current configuration to JSON file."""
        try:
            config_dict = asdict(self.config)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._update_config_from_dict(updates)
        self._validate_configuration()
        self.logger.info("Configuration updated successfully")
    
    def get_stage_config(self, stage_number: int) -> Union[Stage1Config, Stage2Config, Stage3Config, Stage4Config]:
        """Get configuration for a specific stage."""
        if stage_number == 1:
            return self.config.stage1
        elif stage_number == 2:
            return self.config.stage2
        elif stage_number == 3:
            return self.config.stage3
        elif stage_number == 4:
            return self.config.stage4
        else:
            raise ValueError(f"Invalid stage number: {stage_number}")
    
    def create_development_config(self) -> None:
        """Create development-friendly configuration."""
        self.config.environment = "development"
        self.config.processing_limits.max_newsletters_total = 5
        self.config.stage2.batch_size = 2
        self.config.error_handling.continue_on_errors = True
        self.config.output.generate_summary_reports = True
        self.config.error_handling.log_level = "DEBUG"
    
    def create_production_config(self) -> None:
        """Create production-ready configuration."""
        self.config.environment = "production"
        self.config.processing_limits.max_newsletters_total = None  # No limit
        self.config.stage2.batch_size = 10
        self.config.error_handling.continue_on_errors = False
        self.config.output.cleanup_intermediate_files = True
        self.config.error_handling.log_level = "INFO"
    
    def get_directory_paths(self) -> Dict[str, Path]:
        """Get all configured directory paths."""
        base_dir = Path(self.config.output.base_output_dir)
        
        return {
            'base': base_dir,
            'structured': base_dir / self.config.output.structured_subdir,
            'enhanced': base_dir / self.config.output.enhanced_subdir,
            'normalized': base_dir / self.config.output.normalized_subdir,
            'analysis': base_dir / self.config.output.analysis_subdir
        }


def load_configuration(config_file: Optional[str] = None) -> PipelineConfiguration:
    """
    Convenience function to load pipeline configuration.
    
    Args:
        config_file: Optional path to JSON configuration file
        
    Returns:
        Loaded and validated configuration
    """
    manager = ConfigurationManager(config_file)
    return manager.get_config()


def create_default_config_file(output_file: str) -> None:
    """
    Create a default configuration file for customization.
    
    Args:
        output_file: Path where to save the default configuration
    """
    config = PipelineConfiguration()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)
    
    print(f"Default configuration saved to {output_file}")
    print("Customize the configuration and load it with ConfigurationManager()")


if __name__ == "__main__":
    """Configuration management utilities."""
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create-default":
        # Create default configuration file
        output_file = sys.argv[2] if len(sys.argv) > 2 else "pipeline_config.json"
        create_default_config_file(output_file)
        
    else:
        # Test configuration loading
        print("🔧 Testing configuration system...")
        
        try:
            # Test basic configuration
            manager = ConfigurationManager()
            config = manager.get_config()
            
            print(f"✅ Configuration loaded successfully")
            print(f"   Environment: {config.environment}")
            print(f"   Stage 2 model: {config.stage2.model}")
            print(f"   Max newsletters: {config.processing_limits.max_newsletters_total or 'unlimited'}")
            print(f"   API key configured: {'Yes' if config.anthropic_api_key else 'No'}")
            
            # Test directory creation
            paths = manager.get_directory_paths()
            for name, path in paths.items():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"   {name} directory: {path} ✅")
                except Exception as e:
                    print(f"   {name} directory: {path} ❌ ({e})")
            
            print("\\n🔧 Configuration system test completed")
            
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            import traceback
            traceback.print_exc()