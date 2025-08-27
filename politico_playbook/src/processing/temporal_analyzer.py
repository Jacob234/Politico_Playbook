#!/usr/bin/env python3
"""
Stage 4 of 4-Stage Political Newsletter Processing Pipeline: Temporal Analyzer

Creates graph-ready data and time series analysis from normalized database objects.
Generates network graphs, temporal trends, and political intelligence insights.

Pipeline Stage 4: Database Cleaned Data → Graph/Time Series Ready
Input: Normalized entities with temporal context from Stage 3
Output: Graph nodes/edges, time series data, political intelligence reports
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import networkx as nx
from itertools import combinations


@dataclass
class GraphNode:
    """Node in the political network graph."""
    node_id: str
    node_type: str  # person, organization, story
    label: str
    category: str
    attributes: Dict[str, Any]
    first_appeared: str
    last_appeared: str
    activity_score: float
    influence_score: float
    centrality_metrics: Dict[str, float]


@dataclass
class GraphEdge:
    """Edge in the political network graph."""
    source_id: str
    target_id: str
    edge_type: str
    relationship_strength: float
    first_observed: str
    last_observed: str
    interaction_count: int
    contexts: List[Dict]
    temporal_pattern: str  # increasing, decreasing, stable, sporadic


@dataclass
class TimeSeriesPoint:
    """Data point for temporal analysis."""
    date: str
    entity_id: str
    entity_name: str
    activity_type: str
    activity_intensity: float
    context: str
    newsletter_id: str


@dataclass
class PoliticalTrend:
    """Identified political trend over time."""
    trend_id: str
    trend_name: str
    start_date: str
    end_date: str
    peak_date: str
    trend_strength: float
    key_entities: List[str]
    description: str
    trend_category: str  # rising_influence, declining_activity, new_relationship, etc.


@dataclass
class InfluenceNetwork:
    """Political influence network analysis."""
    network_id: str
    network_name: str
    central_figures: List[str]
    network_density: float
    clustering_coefficient: float
    average_path_length: float
    key_relationships: List[Dict]
    network_evolution: List[Dict]  # Snapshots over time


class TemporalAnalyzer:
    """
    Stage 4 processor: Create graph and time series analysis from normalized data.
    
    Key functions:
    1. Build political network graphs from relationships
    2. Generate time series data for trend analysis  
    3. Calculate influence and centrality metrics
    4. Identify emerging trends and patterns
    5. Create visualization-ready data exports
    """
    
    def __init__(self):
        """Initialize the temporal analyzer."""
        
        # Network analysis
        self.political_graph = nx.Graph()
        self.temporal_graph_snapshots = {}  # date -> nx.Graph
        
        # Entity tracking
        self.entity_registry = {}  # entity_id -> entity_data
        self.activity_timeline = []  # chronological activity points
        self.relationship_evolution = {}  # relationship -> timeline
        
        # Analysis results
        self.influence_networks = {}
        self.political_trends = {}
        self.time_series_data = []
        
        # Processing statistics
        self.processing_stats = {
            'newsletters_analyzed': 0,
            'graph_nodes': 0,
            'graph_edges': 0,
            'trends_identified': 0,
            'time_periods_covered': 0
        }
    
    def process_newsletter_batch(self, input_dir: Path) -> Dict:
        """
        Stage 4: Process batch of normalized newsletters for temporal analysis.
        
        Args:
            input_dir: Directory containing Stage 3 normalized newsletters
            
        Returns:
            Comprehensive temporal analysis results
        """
        print(f"📈 Stage 4: Building temporal analysis from normalized data")
        
        # Load all normalized newsletters
        normalized_files = list(input_dir.glob("normalized_*.json"))
        newsletters_data = []
        
        for file_path in normalized_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    newsletter = json.load(f)
                    if 'database_normalized_results' in newsletter:
                        newsletters_data.append(newsletter)
            except Exception as e:
                print(f"⚠️ Error loading {file_path}: {e}")
        
        print(f"📊 Loaded {len(newsletters_data)} normalized newsletters for analysis")
        
        # Build comprehensive temporal analysis
        self._build_entity_registry(newsletters_data)
        self._build_political_graph(newsletters_data)
        self._generate_time_series_data(newsletters_data)
        self._analyze_influence_networks()
        self._identify_political_trends()
        
        # Generate analysis summary
        analysis_results = self._compile_analysis_results()
        
        print(f"📈 Stage 4 analysis complete:")
        print(f"  Graph nodes: {len(self.political_graph.nodes)}")
        print(f"  Graph edges: {len(self.political_graph.edges)}")
        print(f"  Time series points: {len(self.time_series_data)}")
        print(f"  Political trends: {len(self.political_trends)}")
        print(f"  Influence networks: {len(self.influence_networks)}")
        
        return analysis_results
    
    def _build_entity_registry(self, newsletters_data: List[Dict]) -> None:
        """Build comprehensive entity registry from normalized data."""
        print("🗂️ Building entity registry...")
        
        for newsletter in newsletters_data:
            normalized_results = newsletter.get('database_normalized_results', {})
            newsletter_date = normalized_results.get('processing_info', {}).get('newsletter_date', '')
            
            # Process people
            for person in normalized_results.get('people', []):
                entity_id = person.get('entity_id')
                if entity_id:
                    if entity_id not in self.entity_registry:
                        self.entity_registry[entity_id] = {
                            'type': 'person',
                            'data': person,
                            'activity_dates': [],
                            'relationships': [],
                            'influence_score': 0.0
                        }
                    
                    self.entity_registry[entity_id]['activity_dates'].append(newsletter_date)
            
            # Process organizations  
            for org in normalized_results.get('organizations', []):
                entity_id = org.get('organization_id')
                if entity_id:
                    if entity_id not in self.entity_registry:
                        self.entity_registry[entity_id] = {
                            'type': 'organization', 
                            'data': org,
                            'activity_dates': [],
                            'relationships': [],
                            'influence_score': 0.0
                        }
                    
                    self.entity_registry[entity_id]['activity_dates'].append(newsletter_date)
            
            # Process stories
            for story in normalized_results.get('stories_and_topics', []):
                entity_id = story.get('story_id')
                if entity_id:
                    if entity_id not in self.entity_registry:
                        self.entity_registry[entity_id] = {
                            'type': 'story',
                            'data': story,
                            'activity_dates': [],
                            'relationships': [],
                            'influence_score': 0.0
                        }
                    
                    self.entity_registry[entity_id]['activity_dates'].append(newsletter_date)
        
        print(f"  📋 Registry built: {len(self.entity_registry)} unique entities")
    
    def _build_political_graph(self, newsletters_data: List[Dict]) -> None:
        """Build political network graph from relationships."""
        print("🕸️ Building political network graph...")
        
        # Add nodes for all entities
        for entity_id, entity_info in self.entity_registry.items():
            entity_data = entity_info['data']
            
            if entity_info['type'] == 'person':
                label = entity_data.get('canonical_name', 'Unknown')
                category = entity_data.get('category', 'unknown')
                attributes = {
                    'employer': entity_data.get('current_employer'),
                    'role': entity_data.get('current_role'),
                    'party': entity_data.get('party_affiliation'),
                    'state': entity_data.get('state'),
                    'mention_count': entity_data.get('mention_count', 0),
                    'confidence': entity_data.get('confidence_average', 0.0)
                }
            elif entity_info['type'] == 'organization':
                label = entity_data.get('canonical_name', 'Unknown')
                category = entity_data.get('organization_type', 'unknown')
                attributes = {
                    'activity': entity_data.get('primary_activity'),
                    'mention_count': entity_data.get('mention_count', 0),
                    'confidence': entity_data.get('confidence_average', 0.0)
                }
            else:  # story
                label = entity_data.get('canonical_topic', 'Unknown')
                category = entity_data.get('story_category', 'general')
                attributes = {
                    'significance': entity_data.get('significance_score', 0.0),
                    'report_count': entity_data.get('report_count', 0)
                }
            
            self.political_graph.add_node(entity_id, 
                                        label=label,
                                        type=entity_info['type'],
                                        category=category,
                                        **attributes)
        
        # Add edges from relationships
        for newsletter in newsletters_data:
            normalized_results = newsletter.get('database_normalized_results', {})
            
            for relationship in normalized_results.get('relationships', []):
                subject_id = relationship.get('subject_entity_id')
                object_id = relationship.get('object_entity_id')
                
                if subject_id and object_id and subject_id in self.entity_registry and object_id in self.entity_registry:
                    # Calculate relationship strength
                    strength = relationship.get('confidence_average', 0.0) * relationship.get('observation_count', 1)
                    
                    # Add or update edge
                    if self.political_graph.has_edge(subject_id, object_id):
                        # Update existing edge
                        edge_data = self.political_graph[subject_id][object_id]
                        edge_data['weight'] = edge_data.get('weight', 0) + strength
                        edge_data['interaction_count'] = edge_data.get('interaction_count', 0) + 1
                    else:
                        # Add new edge
                        self.political_graph.add_edge(subject_id, object_id,
                                                    weight=strength,
                                                    relationship_type=relationship.get('relationship_type', 'interaction'),
                                                    interaction_count=1,
                                                    first_observed=relationship.get('first_observed'),
                                                    last_observed=relationship.get('last_observed'))
        
        print(f"  🕸️ Graph built: {len(self.political_graph.nodes)} nodes, {len(self.political_graph.edges)} edges")
    
    def _generate_time_series_data(self, newsletters_data: List[Dict]) -> None:
        """Generate time series data points for trend analysis."""
        print("📈 Generating time series data...")
        
        self.time_series_data = []
        
        for newsletter in newsletters_data:
            newsletter_id = newsletter.get('file_name', 'unknown')
            normalized_results = newsletter.get('database_normalized_results', {})
            newsletter_date = normalized_results.get('processing_info', {}).get('newsletter_date', '')
            
            # Create time series points for people activities
            for person in normalized_results.get('people', []):
                # Calculate activity intensity based on mention frequency and context
                base_intensity = person.get('confidence_average', 0.0)
                mention_boost = min(person.get('mention_count', 1) / 5.0, 1.0)  # Cap at 1.0
                activity_intensity = base_intensity * (1 + mention_boost)
                
                # Determine activity type based on person's role/category
                activity_type = self._classify_person_activity_type(person)
                
                time_point = TimeSeriesPoint(
                    date=newsletter_date,
                    entity_id=person.get('entity_id', ''),
                    entity_name=person.get('canonical_name', 'Unknown'),
                    activity_type=activity_type,
                    activity_intensity=activity_intensity,
                    context=person.get('newsletter_appearances', [{}])[-1].get('activity', ''),
                    newsletter_id=newsletter_id
                )
                
                self.time_series_data.append(time_point)
            
            # Create time series points for organizational activities
            for org in normalized_results.get('organizations', []):
                activity_intensity = org.get('confidence_average', 0.0)
                
                time_point = TimeSeriesPoint(
                    date=newsletter_date,
                    entity_id=org.get('organization_id', ''),
                    entity_name=org.get('canonical_name', 'Unknown'),
                    activity_type='organizational_activity',
                    activity_intensity=activity_intensity,
                    context=org.get('newsletter_appearances', [{}])[-1].get('activity', ''),
                    newsletter_id=newsletter_id
                )
                
                self.time_series_data.append(time_point)
        
        print(f"  📊 Generated {len(self.time_series_data)} time series data points")
    
    def _classify_person_activity_type(self, person: Dict) -> str:
        """Classify person's activity type for time series analysis."""
        category = person.get('category', 'unknown')
        role = person.get('current_role', '').lower()
        
        if category == 'political_official':
            if 'president' in role:
                return 'executive_activity'
            elif any(title in role for title in ['senator', 'representative']):
                return 'legislative_activity'
            elif any(title in role for title in ['secretary', 'director', 'administrator']):
                return 'administrative_activity'
            else:
                return 'political_activity'
        elif category == 'journalist':
            return 'media_activity'
        elif category in ['staff', 'political_staff']:
            return 'staff_activity'
        elif category == 'lobbyist':
            return 'lobbying_activity'
        else:
            return 'general_activity'
    
    def _analyze_influence_networks(self) -> None:
        """Analyze influence networks and calculate centrality metrics."""
        print("🎯 Analyzing influence networks...")
        
        if len(self.political_graph.nodes) == 0:
            print("  ⚠️ No graph nodes found. Skipping network analysis.")
            return
        
        # Calculate centrality metrics
        try:
            degree_centrality = nx.degree_centrality(self.political_graph)
            betweenness_centrality = nx.betweenness_centrality(self.political_graph, k=min(100, len(self.political_graph.nodes)))
            closeness_centrality = nx.closeness_centrality(self.political_graph)
            eigenvector_centrality = nx.eigenvector_centrality(self.political_graph, max_iter=1000)
        except Exception as e:
            print(f"  ⚠️ Error calculating centrality metrics: {e}")
            # Fallback to degree centrality only
            degree_centrality = nx.degree_centrality(self.political_graph)
            betweenness_centrality = {node: 0.0 for node in self.political_graph.nodes}
            closeness_centrality = {node: 0.0 for node in self.political_graph.nodes}
            eigenvector_centrality = {node: 0.0 for node in self.political_graph.nodes}
        
        # Update entity influence scores
        for entity_id in self.entity_registry.keys():
            if entity_id in degree_centrality:
                influence_score = (
                    degree_centrality[entity_id] * 0.3 +
                    betweenness_centrality[entity_id] * 0.3 +
                    closeness_centrality[entity_id] * 0.2 +
                    eigenvector_centrality[entity_id] * 0.2
                )
                self.entity_registry[entity_id]['influence_score'] = influence_score
                self.entity_registry[entity_id]['centrality_metrics'] = {
                    'degree': degree_centrality[entity_id],
                    'betweenness': betweenness_centrality[entity_id],
                    'closeness': closeness_centrality[entity_id],
                    'eigenvector': eigenvector_centrality[entity_id]
                }
        
        # Identify key influence networks (communities)
        try:
            communities = nx.community.greedy_modularity_communities(self.political_graph)
            
            for i, community in enumerate(communities):
                if len(community) >= 3:  # Only consider communities with 3+ members
                    # Find central figures in this community
                    subgraph = self.political_graph.subgraph(community)
                    sub_centrality = nx.degree_centrality(subgraph)
                    central_figures = sorted(sub_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                    
                    # Calculate network metrics
                    network_density = nx.density(subgraph)
                    clustering_coeff = nx.average_clustering(subgraph)
                    
                    try:
                        avg_path_length = nx.average_shortest_path_length(subgraph) if nx.is_connected(subgraph) else 0.0
                    except:
                        avg_path_length = 0.0
                    
                    network_name = self._generate_network_name([fig[0] for fig in central_figures[:3]])
                    
                    influence_network = InfluenceNetwork(
                        network_id=f"network_{i+1}",
                        network_name=network_name,
                        central_figures=[fig[0] for fig in central_figures],
                        network_density=network_density,
                        clustering_coefficient=clustering_coeff,
                        average_path_length=avg_path_length,
                        key_relationships=[],  # TODO: Extract key relationships
                        network_evolution=[]   # TODO: Track evolution over time
                    )
                    
                    self.influence_networks[f"network_{i+1}"] = influence_network
        
        except Exception as e:
            print(f"  ⚠️ Error in community detection: {e}")
        
        print(f"  🎯 Identified {len(self.influence_networks)} influence networks")
    
    def _generate_network_name(self, central_figures: List[str]) -> str:
        """Generate descriptive name for influence network."""
        if not central_figures:
            return "Unknown Network"
        
        # Get entity names from registry
        names = []
        for entity_id in central_figures:
            if entity_id in self.entity_registry:
                entity_data = self.entity_registry[entity_id]['data']
                if 'canonical_name' in entity_data:
                    name = entity_data['canonical_name']
                    # Get last name for network naming
                    last_name = name.split()[-1] if ' ' in name else name
                    names.append(last_name)
        
        if len(names) == 1:
            return f"{names[0]} Network"
        elif len(names) == 2:
            return f"{names[0]}-{names[1]} Network"
        else:
            return f"{names[0]}-{names[1]}-{names[2]} Network"
    
    def _identify_political_trends(self) -> None:
        """Identify political trends from time series data."""
        print("📊 Identifying political trends...")
        
        if not self.time_series_data:
            print("  ⚠️ No time series data available. Skipping trend analysis.")
            return
        
        # Convert to DataFrame for easier analysis
        df_data = []
        for point in self.time_series_data:
            df_data.append({
                'date': point.date,
                'entity_id': point.entity_id,
                'entity_name': point.entity_name,
                'activity_type': point.activity_type,
                'activity_intensity': point.activity_intensity,
                'context': point.context,
                'newsletter_id': point.newsletter_id
            })
        
        df = pd.DataFrame(df_data)
        
        # Ensure date column is datetime
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception as e:
            print(f"  ⚠️ Error parsing dates: {e}")
            return
        
        # Group by entity and analyze trends
        for entity_id in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity_id].copy()
            
            if len(entity_data) < 2:  # Need at least 2 points for trend analysis
                continue
            
            entity_data = entity_data.sort_values('date')
            entity_name = entity_data['entity_name'].iloc[0]
            
            # Calculate trend metrics
            activity_values = entity_data['activity_intensity'].values
            trend_slope = np.polyfit(range(len(activity_values)), activity_values, 1)[0]
            
            # Identify trend type
            if abs(trend_slope) < 0.1:
                trend_type = 'stable_activity'
            elif trend_slope > 0.1:
                trend_type = 'rising_influence'
            else:
                trend_type = 'declining_activity'
            
            # Find peak activity
            peak_idx = np.argmax(activity_values)
            peak_date = entity_data.iloc[peak_idx]['date'].isoformat()
            
            trend = PoliticalTrend(
                trend_id=f"trend_{entity_id}",
                trend_name=f"{entity_name} - {trend_type.replace('_', ' ').title()}",
                start_date=entity_data['date'].min().isoformat(),
                end_date=entity_data['date'].max().isoformat(),
                peak_date=peak_date,
                trend_strength=abs(trend_slope) * np.max(activity_values),
                key_entities=[entity_id],
                description=self._generate_trend_description(entity_name, trend_type, trend_slope),
                trend_category=trend_type
            )
            
            # Only include significant trends
            if trend.trend_strength > 0.5:  # Minimum threshold
                self.political_trends[trend.trend_id] = trend
        
        print(f"  📈 Identified {len(self.political_trends)} significant political trends")
    
    def _generate_trend_description(self, entity_name: str, trend_type: str, slope: float) -> str:
        """Generate descriptive text for political trends."""
        if trend_type == 'rising_influence':
            return f"{entity_name} shows increasing political activity and influence over the analyzed period (slope: {slope:.3f})"
        elif trend_type == 'declining_activity':
            return f"{entity_name} shows decreasing political activity and visibility over the analyzed period (slope: {slope:.3f})"
        else:
            return f"{entity_name} maintains stable political activity levels over the analyzed period (slope: {slope:.3f})"
    
    def _compile_analysis_results(self) -> Dict:
        """Compile comprehensive analysis results."""
        # Convert graph to serializable format
        graph_nodes = []
        for node_id, data in self.political_graph.nodes(data=True):
            entity_info = self.entity_registry.get(node_id, {})
            
            graph_node = GraphNode(
                node_id=node_id,
                node_type=data.get('type', 'unknown'),
                label=data.get('label', 'Unknown'),
                category=data.get('category', 'unknown'),
                attributes=data,
                first_appeared=entity_info.get('data', {}).get('first_mentioned', ''),
                last_appeared=entity_info.get('data', {}).get('last_mentioned', ''),
                activity_score=len(entity_info.get('activity_dates', [])),
                influence_score=entity_info.get('influence_score', 0.0),
                centrality_metrics=entity_info.get('centrality_metrics', {})
            )
            
            graph_nodes.append(asdict(graph_node))
        
        # Convert graph edges
        graph_edges = []
        for source, target, data in self.political_graph.edges(data=True):
            graph_edge = GraphEdge(
                source_id=source,
                target_id=target,
                edge_type=data.get('relationship_type', 'interaction'),
                relationship_strength=data.get('weight', 0.0),
                first_observed=data.get('first_observed', ''),
                last_observed=data.get('last_observed', ''),
                interaction_count=data.get('interaction_count', 0),
                contexts=[],  # TODO: Add context information
                temporal_pattern='stable'  # TODO: Analyze temporal patterns
            )
            
            graph_edges.append(asdict(graph_edge))
        
        # Compile final results
        analysis_results = {
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'stage': 'temporal_analysis_complete',
                'processing_stats': self.processing_stats
            },
            'graph_data': {
                'nodes': graph_nodes,
                'edges': graph_edges,
                'network_metrics': {
                    'total_nodes': len(graph_nodes),
                    'total_edges': len(graph_edges),
                    'network_density': nx.density(self.political_graph) if len(self.political_graph.nodes) > 0 else 0.0,
                    'connected_components': nx.number_connected_components(self.political_graph)
                }
            },
            'time_series_data': [asdict(point) for point in self.time_series_data],
            'political_trends': {trend_id: asdict(trend) for trend_id, trend in self.political_trends.items()},
            'influence_networks': {net_id: asdict(network) for net_id, network in self.influence_networks.items()},
            'entity_registry': self._serialize_entity_registry()
        }
        
        return analysis_results
    
    def _serialize_entity_registry(self) -> Dict:
        """Serialize entity registry for JSON output."""
        serialized = {}
        for entity_id, entity_info in self.entity_registry.items():
            serialized[entity_id] = {
                'type': entity_info['type'],
                'data': entity_info['data'],
                'influence_score': entity_info.get('influence_score', 0.0),
                'centrality_metrics': entity_info.get('centrality_metrics', {}),
                'activity_summary': {
                    'total_appearances': len(entity_info.get('activity_dates', [])),
                    'active_date_range': {
                        'start': min(entity_info.get('activity_dates', []), default=''),
                        'end': max(entity_info.get('activity_dates', []), default='')
                    }
                }
            }
        
        return serialized
    
    def export_analysis_results(self, output_dir: Path, analysis_results: Dict) -> Dict[str, str]:
        """Export analysis results in multiple formats for visualization."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        files_created = {}
        
        # Export complete analysis results
        complete_file = output_dir / "temporal_analysis_complete.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        files_created['complete_analysis'] = str(complete_file)
        
        # Export graph data for visualization (Gephi/Cytoscape format)
        graph_file = output_dir / "political_network_graph.json"
        graph_data = {
            'nodes': analysis_results['graph_data']['nodes'],
            'edges': analysis_results['graph_data']['edges']
        }
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        files_created['graph_data'] = str(graph_file)
        
        # Export time series data as CSV
        time_series_file = output_dir / "political_time_series.csv"
        time_series_df = pd.DataFrame(analysis_results['time_series_data'])
        time_series_df.to_csv(time_series_file, index=False)
        files_created['time_series_csv'] = str(time_series_file)
        
        # Export trends summary
        trends_file = output_dir / "political_trends.json"
        with open(trends_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results['political_trends'], f, indent=2, ensure_ascii=False)
        files_created['trends'] = str(trends_file)
        
        # Export influence networks
        networks_file = output_dir / "influence_networks.json"
        with open(networks_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results['influence_networks'], f, indent=2, ensure_ascii=False)
        files_created['influence_networks'] = str(networks_file)
        
        return files_created


def analyze_political_newsletters_stage4(input_dir: Path, output_dir: Path) -> Dict:
    """
    Run Stage 4 temporal analysis on normalized newsletter data.
    
    Args:
        input_dir: Directory containing Stage 3 normalized newsletters
        output_dir: Directory to save Stage 4 analysis results
        
    Returns:
        Complete temporal analysis results
    """
    analyzer = TemporalAnalyzer()
    
    print(f"📈 Stage 4: Political Newsletter Temporal Analysis")
    print("=" * 55)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Run analysis
    analysis_results = analyzer.process_newsletter_batch(input_dir)
    
    # Export results
    export_files = analyzer.export_analysis_results(output_dir, analysis_results)
    
    print(f"\n📈 STAGE 4 ANALYSIS SUMMARY")
    print(f"Graph nodes (entities): {len(analysis_results['graph_data']['nodes'])}")
    print(f"Graph edges (relationships): {len(analysis_results['graph_data']['edges'])}")
    print(f"Time series data points: {len(analysis_results['time_series_data'])}")
    print(f"Political trends identified: {len(analysis_results['political_trends'])}")
    print(f"Influence networks: {len(analysis_results['influence_networks'])}")
    
    print(f"\n📊 Analysis files exported:")
    for analysis_type, file_path in export_files.items():
        print(f"  {analysis_type}: {file_path}")
    
    return analysis_results


if __name__ == "__main__":
    """Test Stage 4 temporal analysis on normalized newsletters."""
    
    # Configuration
    base_dir = Path(__file__).parent.parent.parent
    input_dir = base_dir / "data" / "structured" / "database_normalized"  # Stage 3 output
    output_dir = base_dir / "data" / "analysis" / "temporal_results"  # Stage 4 output
    
    print("📈 Political Newsletter Temporal Analyzer - Stage 4")
    print("=" * 60)
    
    # Run analysis
    try:
        analyze_political_newsletters_stage4(input_dir, output_dir)
        print("\n✅ Stage 4 temporal analysis completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()