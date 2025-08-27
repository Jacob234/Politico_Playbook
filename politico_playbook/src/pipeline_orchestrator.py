#!/usr/bin/env python3
"""
4-Stage Political Newsletter Processing Pipeline Orchestrator

Coordinates the complete transformation from raw HTML newsletters to graph/time series analysis.
Manages all four stages with error handling, progress tracking, and configuration management.

Pipeline Overview:
Stage 1: Raw HTML → Structured (Basic newsletter metadata and clean text)
Stage 2: Structured → Enhanced Structure (Claude Sonnet 4 entity extraction)  
Stage 3: Enhanced Structure → Database Cleaned Data (Entity normalization & temporal context)
Stage 4: Database Cleaned Data → Graph/Time Series Ready (Network analysis & trend identification)
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import time
import traceback

# Import stage processors
from processing.claude_nlp_processor import ClaudeNLPProcessor, process_newsletter_batch
from processing.database_normalizer import DatabaseNormalizer, process_newsletter_batch_stage3
from processing.temporal_analyzer import TemporalAnalyzer, analyze_political_newsletters_stage4


@dataclass
class PipelineConfig:
    """Configuration for the 4-stage pipeline."""
    
    # Data directories
    raw_data_dir: str = "data/raw"
    structured_data_dir: str = "data/structured" 
    enhanced_data_dir: str = "data/structured/claude_enhanced"
    normalized_data_dir: str = "data/structured/database_normalized"
    analysis_output_dir: str = "data/analysis/temporal_results"
    
    # Stage 2 Configuration (Claude NLP)
    claude_model: str = "claude-sonnet-4-20250514"
    claude_temperature: float = 0.3
    claude_max_tokens: int = 8192
    
    # Processing limits
    max_newsletters_per_batch: Optional[int] = None
    stage_2_batch_size: int = 10  # Process in smaller batches for cost control
    
    # Error handling
    max_retries_per_stage: int = 3
    skip_errors: bool = True
    error_log_file: str = "pipeline_errors.log"
    
    # Output configuration
    export_intermediate_results: bool = True
    generate_summary_reports: bool = True


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage_number: int
    stage_name: str
    success: bool
    files_processed: int
    files_failed: int
    processing_time_seconds: float
    output_directory: str
    error_summary: List[str]
    stage_metrics: Dict[str, Any]


@dataclass
class PipelineResults:
    """Complete pipeline execution results."""
    pipeline_id: str
    start_time: str
    end_time: str
    total_processing_time: str
    configuration: Dict[str, Any]
    stage_results: List[StageResult]
    final_outputs: Dict[str, str]
    success: bool
    error_summary: List[str]


class PipelineOrchestrator:
    """
    Orchestrates the complete 4-stage political newsletter processing pipeline.
    
    Handles:
    - Stage coordination and dependency management
    - Error handling and recovery
    - Progress tracking and logging
    - Configuration management
    - Resource optimization
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline orchestrator.
        
        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or PipelineConfig()
        
        # Setup directories
        self.base_dir = Path(__file__).parent.parent
        self._setup_directories()
        
        # Initialize stage processors
        self.stage_processors = {}
        self.stage_results = []
        
        # Pipeline tracking
        self.pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = None
        self.end_time = None
        
        print(f"🚀 Pipeline Orchestrator initialized")
        print(f"   Pipeline ID: {self.pipeline_id}")
        print(f"   Configuration: {len([k for k, v in asdict(self.config).items() if v is not None])} settings active")
    
    def _setup_directories(self) -> None:
        """Create all required directories."""
        directories = [
            self.base_dir / self.config.structured_data_dir,
            self.base_dir / self.config.enhanced_data_dir,
            self.base_dir / self.config.normalized_data_dir,
            self.base_dir / self.config.analysis_output_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def run_complete_pipeline(self, input_source: Optional[str] = None) -> PipelineResults:
        """
        Execute the complete 4-stage pipeline.
        
        Args:
            input_source: Optional specific input directory or file
            
        Returns:
            Complete pipeline results with metrics and outputs
        """
        print(f"🎯 Starting complete 4-stage pipeline execution")
        print(f"=" * 60)
        
        self.start_time = datetime.now()
        pipeline_success = True
        
        try:
            # Stage 1: Check for structured data (assumes Stage 1 already complete)
            stage1_result = self._verify_stage1_data()
            self.stage_results.append(stage1_result)
            
            if not stage1_result.success:
                raise Exception("Stage 1 data verification failed")
            
            # Stage 2: Enhanced Structure (Claude NLP)
            stage2_result = self._execute_stage2()
            self.stage_results.append(stage2_result)
            
            if not stage2_result.success and not self.config.skip_errors:
                raise Exception("Stage 2 processing failed")
            
            # Stage 3: Database Normalization
            stage3_result = self._execute_stage3()
            self.stage_results.append(stage3_result)
            
            if not stage3_result.success and not self.config.skip_errors:
                raise Exception("Stage 3 processing failed")
            
            # Stage 4: Temporal Analysis
            stage4_result = self._execute_stage4()
            self.stage_results.append(stage4_result)
            
            if not stage4_result.success and not self.config.skip_errors:
                raise Exception("Stage 4 processing failed")
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            pipeline_success = False
            traceback.print_exc()
        
        self.end_time = datetime.now()
        
        # Compile final results
        results = self._compile_pipeline_results(pipeline_success)
        
        # Generate summary report
        if self.config.generate_summary_reports:
            self._generate_summary_report(results)
        
        print(f"🏁 Pipeline execution completed")
        print(f"   Success: {'✅ Yes' if results.success else '❌ No'}")
        print(f"   Total time: {results.total_processing_time}")
        
        return results
    
    def _verify_stage1_data(self) -> StageResult:
        """Verify Stage 1 structured data exists."""
        print(f"📋 Stage 1: Verifying structured data availability...")
        
        start_time = time.time()
        structured_dir = self.base_dir / self.config.structured_data_dir
        
        # Find structured newsletter files
        json_files = list(structured_dir.glob("*.json"))
        
        # Filter out Stage 2+ files
        stage1_files = [f for f in json_files if not f.name.startswith(('claude_', 'normalized_'))]
        
        processing_time = time.time() - start_time
        
        if stage1_files:
            print(f"  ✅ Found {len(stage1_files)} structured newsletter files")
            
            return StageResult(
                stage_number=1,
                stage_name="Data Verification",
                success=True,
                files_processed=len(stage1_files),
                files_failed=0,
                processing_time_seconds=processing_time,
                output_directory=str(structured_dir),
                error_summary=[],
                stage_metrics={
                    'newsletters_available': len(stage1_files),
                    'data_source': 'structured_json'
                }
            )
        else:
            print(f"  ❌ No structured newsletter files found in {structured_dir}")
            
            return StageResult(
                stage_number=1,
                stage_name="Data Verification", 
                success=False,
                files_processed=0,
                files_failed=1,
                processing_time_seconds=processing_time,
                output_directory=str(structured_dir),
                error_summary=["No structured newsletter files found"],
                stage_metrics={}
            )
    
    def _execute_stage2(self) -> StageResult:
        """Execute Stage 2: Enhanced Structure (Claude NLP)."""
        print(f"🤖 Stage 2: Enhanced Structure (Claude NLP Processing)...")
        
        start_time = time.time()
        input_dir = self.base_dir / self.config.structured_data_dir
        output_dir = self.base_dir / self.config.enhanced_data_dir
        
        try:
            # Initialize Claude processor with configuration
            self.stage_processors['claude'] = ClaudeNLPProcessor(
                model=self.config.claude_model
            )
            
            # Process newsletters in batches for cost control
            processed_count, error_list = process_newsletter_batch(
                input_dir, 
                output_dir, 
                max_newsletters=self.config.max_newsletters_per_batch
            )
            
            processing_time = time.time() - start_time
            
            # Get cost summary from processor
            cost_summary = self.stage_processors['claude'].get_cost_summary()
            
            print(f"  ✅ Stage 2 completed: {processed_count} newsletters processed")
            
            return StageResult(
                stage_number=2,
                stage_name="Enhanced Structure (Claude NLP)",
                success=len(error_list) == 0,
                files_processed=processed_count,
                files_failed=len(error_list),
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=error_list,
                stage_metrics={
                    'cost_summary': cost_summary,
                    'model_used': self.config.claude_model,
                    'avg_processing_time': processing_time / max(processed_count, 1)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Stage 2 execution error: {e}"
            print(f"  ❌ {error_msg}")
            
            return StageResult(
                stage_number=2,
                stage_name="Enhanced Structure (Claude NLP)",
                success=False,
                files_processed=0,
                files_failed=1,
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=[error_msg],
                stage_metrics={}
            )
    
    def _execute_stage3(self) -> StageResult:
        """Execute Stage 3: Database Normalization."""
        print(f"🗃️ Stage 3: Database Normalization...")
        
        start_time = time.time()
        input_dir = self.base_dir / self.config.enhanced_data_dir
        output_dir = self.base_dir / self.config.normalized_data_dir
        
        try:
            # Process with database normalizer
            processed_count, error_list = process_newsletter_batch_stage3(
                input_dir,
                output_dir,
                max_newsletters=self.config.max_newsletters_per_batch
            )
            
            processing_time = time.time() - start_time
            
            print(f"  ✅ Stage 3 completed: {processed_count} newsletters normalized")
            
            return StageResult(
                stage_number=3,
                stage_name="Database Normalization",
                success=len(error_list) == 0,
                files_processed=processed_count,
                files_failed=len(error_list),
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=error_list,
                stage_metrics={
                    'normalization_type': 'entity_deduplication_temporal_context',
                    'avg_processing_time': processing_time / max(processed_count, 1)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Stage 3 execution error: {e}"
            print(f"  ❌ {error_msg}")
            
            return StageResult(
                stage_number=3,
                stage_name="Database Normalization",
                success=False,
                files_processed=0,
                files_failed=1,
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=[error_msg],
                stage_metrics={}
            )
    
    def _execute_stage4(self) -> StageResult:
        """Execute Stage 4: Temporal Analysis."""
        print(f"📈 Stage 4: Temporal Analysis...")
        
        start_time = time.time()
        input_dir = self.base_dir / self.config.normalized_data_dir
        output_dir = self.base_dir / self.config.analysis_output_dir
        
        try:
            # Run temporal analysis
            analysis_results = analyze_political_newsletters_stage4(input_dir, output_dir)
            
            processing_time = time.time() - start_time
            
            # Extract metrics from analysis results
            graph_metrics = analysis_results.get('graph_data', {}).get('network_metrics', {})
            trends_count = len(analysis_results.get('political_trends', {}))
            networks_count = len(analysis_results.get('influence_networks', {}))
            
            print(f"  ✅ Stage 4 completed: Temporal analysis generated")
            
            return StageResult(
                stage_number=4,
                stage_name="Temporal Analysis",
                success=True,
                files_processed=1,  # Single analysis output
                files_failed=0,
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=[],
                stage_metrics={
                    'graph_nodes': graph_metrics.get('total_nodes', 0),
                    'graph_edges': graph_metrics.get('total_edges', 0),
                    'political_trends': trends_count,
                    'influence_networks': networks_count,
                    'time_series_points': len(analysis_results.get('time_series_data', [])),
                    'network_density': graph_metrics.get('network_density', 0.0)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Stage 4 execution error: {e}"
            print(f"  ❌ {error_msg}")
            
            return StageResult(
                stage_number=4,
                stage_name="Temporal Analysis",
                success=False,
                files_processed=0,
                files_failed=1,
                processing_time_seconds=processing_time,
                output_directory=str(output_dir),
                error_summary=[error_msg],
                stage_metrics={}
            )
    
    def _compile_pipeline_results(self, success: bool) -> PipelineResults:
        """Compile complete pipeline results."""
        
        total_time = self.end_time - self.start_time if self.end_time else timedelta(0)
        
        # Identify final outputs
        final_outputs = {}
        analysis_dir = self.base_dir / self.config.analysis_output_dir
        
        if analysis_dir.exists():
            analysis_files = list(analysis_dir.glob("*.json")) + list(analysis_dir.glob("*.csv"))
            for file_path in analysis_files:
                final_outputs[file_path.stem] = str(file_path)
        
        # Collect all errors
        all_errors = []
        for stage_result in self.stage_results:
            all_errors.extend(stage_result.error_summary)
        
        return PipelineResults(
            pipeline_id=self.pipeline_id,
            start_time=self.start_time.isoformat() if self.start_time else '',
            end_time=self.end_time.isoformat() if self.end_time else '',
            total_processing_time=str(total_time),
            configuration=asdict(self.config),
            stage_results=self.stage_results,
            final_outputs=final_outputs,
            success=success and all(stage.success for stage in self.stage_results),
            error_summary=all_errors
        )
    
    def _generate_summary_report(self, results: PipelineResults) -> None:
        """Generate comprehensive summary report."""
        
        report_file = self.base_dir / self.config.analysis_output_dir / f"{self.pipeline_id}_summary_report.json"
        
        # Create detailed summary
        summary_report = {
            'pipeline_execution': asdict(results),
            'stage_breakdown': {
                f'stage_{stage.stage_number}': {
                    'name': stage.stage_name,
                    'success': stage.success,
                    'performance': {
                        'files_processed': stage.files_processed,
                        'files_failed': stage.files_failed,
                        'processing_time_seconds': stage.processing_time_seconds,
                        'throughput_files_per_second': stage.files_processed / max(stage.processing_time_seconds, 0.1)
                    },
                    'metrics': stage.stage_metrics,
                    'errors': stage.error_summary
                }
                for stage in results.stage_results
            },
            'overall_metrics': self._calculate_overall_metrics(),
            'recommendations': self._generate_recommendations()
        }
        
        # Save report
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Summary report generated: {report_file}")
    
    def _calculate_overall_metrics(self) -> Dict[str, Any]:
        """Calculate overall pipeline performance metrics."""
        
        total_files_processed = sum(stage.files_processed for stage in self.stage_results)
        total_files_failed = sum(stage.files_failed for stage in self.stage_results)
        total_processing_time = sum(stage.processing_time_seconds for stage in self.stage_results)
        
        success_rate = total_files_processed / max(total_files_processed + total_files_failed, 1)
        
        return {
            'total_files_processed': total_files_processed,
            'total_files_failed': total_files_failed,
            'overall_success_rate': success_rate,
            'total_processing_time_seconds': total_processing_time,
            'average_throughput_files_per_second': total_files_processed / max(total_processing_time, 0.1),
            'stages_completed': len([s for s in self.stage_results if s.success]),
            'stages_failed': len([s for s in self.stage_results if not s.success])
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance."""
        
        recommendations = []
        
        # Check for performance issues
        for stage in self.stage_results:
            if stage.files_failed > 0:
                recommendations.append(f"Stage {stage.stage_number} ({stage.stage_name}) had {stage.files_failed} failures - review error logs")
            
            if stage.processing_time_seconds > 300:  # > 5 minutes
                recommendations.append(f"Stage {stage.stage_number} took {stage.processing_time_seconds:.1f}s - consider optimization")
        
        # Check Stage 2 costs if available
        stage2 = next((s for s in self.stage_results if s.stage_number == 2), None)
        if stage2 and 'cost_summary' in stage2.stage_metrics:
            cost_info = stage2.stage_metrics['cost_summary']
            if cost_info.get('total_estimated_cost', 0) > 5.0:  # > $5
                recommendations.append("Stage 2 (Claude NLP) costs are high - consider batch optimization")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Pipeline executed successfully - no optimization recommendations")
        
        return recommendations
    
    def run_single_stage(self, stage_number: int, input_dir: Optional[str] = None, 
                        output_dir: Optional[str] = None) -> StageResult:
        """
        Run a single stage of the pipeline.
        
        Args:
            stage_number: Stage to execute (1-4)
            input_dir: Override input directory
            output_dir: Override output directory
            
        Returns:
            Result from the specified stage
        """
        print(f"🎯 Running single stage: {stage_number}")
        
        if stage_number == 1:
            return self._verify_stage1_data()
        elif stage_number == 2:
            return self._execute_stage2()
        elif stage_number == 3:
            return self._execute_stage3()
        elif stage_number == 4:
            return self._execute_stage4()
        else:
            raise ValueError(f"Invalid stage number: {stage_number}. Must be 1-4.")


def create_default_config() -> PipelineConfig:
    """Create default pipeline configuration."""
    return PipelineConfig()


def run_full_pipeline(config: Optional[PipelineConfig] = None) -> PipelineResults:
    """
    Convenience function to run the complete pipeline with optional configuration.
    
    Args:
        config: Pipeline configuration (uses defaults if None)
        
    Returns:
        Complete pipeline execution results
    """
    orchestrator = PipelineOrchestrator(config)
    return orchestrator.run_complete_pipeline()


if __name__ == "__main__":
    """Run the complete 4-stage pipeline."""
    
    print("🚀 Political Newsletter Processing Pipeline")
    print("=" * 50)
    print("4-Stage Architecture:")
    print("  Stage 1: Raw HTML → Structured")  
    print("  Stage 2: Structured → Enhanced Structure (Claude NLP)")
    print("  Stage 3: Enhanced Structure → Database Cleaned Data")
    print("  Stage 4: Database Cleaned Data → Graph/Time Series Ready")
    print()
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Please set your Anthropic API key:")
        print("export ANTHROPIC_API_KEY=your_api_key_here")
        exit(1)
    
    # Create configuration
    config = PipelineConfig(
        max_newsletters_per_batch=10,  # Limit for testing
        skip_errors=True,              # Continue on errors
        generate_summary_reports=True
    )
    
    # Run complete pipeline
    try:
        results = run_full_pipeline(config)
        
        print(f"\n🏁 PIPELINE COMPLETE!")
        print(f"Success: {'✅ Yes' if results.success else '❌ No'}")
        print(f"Processing time: {results.total_processing_time}")
        print(f"Final outputs: {len(results.final_outputs)} files")
        
        if results.final_outputs:
            print("\n📊 Generated Files:")
            for file_type, file_path in results.final_outputs.items():
                print(f"  {file_type}: {file_path}")
                
        if results.error_summary:
            print(f"\n⚠️ Errors encountered: {len(results.error_summary)}")
            for error in results.error_summary[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        traceback.print_exc()