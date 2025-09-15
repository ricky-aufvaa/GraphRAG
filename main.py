#!/usr/bin/env python3
"""
SimpleKG - Local to Global GraphRAG Implementation
==================================================

This is the main pipeline script for the SimpleKG project, implementing Microsoft's 
Local to Global GraphRAG approach for medical knowledge extraction and querying.

Pipeline Steps:
1. Data Processing & Entity Extraction
2. Graph Construction 
3. Community Detection
4. Community Summarization
5. Query Processing

Usage:
    python main.py --step <step_name>
    python main.py --pipeline  # Run full pipeline
    python main.py --query     # Interactive query mode
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

def run_data_processing():
    """Step 1: Process raw data and extract entities"""
    print("🔄 Step 1: Data Processing & Entity Extraction")
    print("="*50)
    
    from src.dataprocessing.data_processing import main as process_data
    from src.dataprocessing.er_extraction import main as extract_entities
    
    # Process raw data into chunks
    print("\n📄 Processing raw data...")
    process_data()
    
    # Extract entities and relationships
    print("\n🧠 Extracting entities and relationships...")
    extract_entities()

def run_graph_construction():
    """Step 2: Build knowledge graph in Neo4j"""
    print("🔄 Step 2: Graph Construction")
    print("="*50)
    
    from src.graph_construction.graph_construction import main as build_graph
    build_graph()

def run_community_detection():
    """Step 3: Detect semantic communities"""
    print("🔄 Step 3: Community Detection")
    print("="*50)
    
    from src.community_detection.community_detection import main as detect_communities
    detect_communities()

def run_community_summarization():
    """Step 4: Generate community summaries with LLM"""
    print("🔄 Step 4: Community Summarization")
    print("="*50)
    
    from src.summarisation.community_summarisation import main as summarize_communities
    summarize_communities()

def run_query_processing():
    """Step 5: Interactive query system"""
    print("🔄 Step 5: Query Processing")
    print("="*50)
    
    from src.query_processing.query_processing import main as query_system
    query_system()

def run_full_pipeline():
    """Run the complete GraphRAG pipeline"""
    print("🚀 SIMPLEKG - LOCAL TO GLOBAL GRAPHRAG PIPELINE")
    print("="*60)
    print("📋 Running complete pipeline...")
    
    try:
        # Step 1: Data Processing & Entity Extraction
        run_data_processing()
        
        # Step 2: Graph Construction
        run_graph_construction()
        
        # Step 3: Community Detection
        run_community_detection()
        
        # Step 4: Community Summarization
        run_community_summarization()
        
        print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("✅ All steps completed. You can now:")
        print("   1. Run queries: python main.py --query")
        print("   2. View Neo4j Browser: http://localhost:7474")
        print("   3. Check output files in data/graphs/")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed at step: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="SimpleKG - Local to Global GraphRAG Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --pipeline              # Run full pipeline
  python main.py --step data_processing  # Run specific step
  python main.py --query                 # Interactive query mode
  
Pipeline Steps:
  data_processing     - Process raw data and extract entities
  graph_construction  - Build knowledge graph in Neo4j
  community_detection - Detect semantic communities
  summarization      - Generate community summaries
  query_processing   - Interactive query system
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pipeline', action='store_true',
                      help='Run the complete GraphRAG pipeline')
    group.add_argument('--step', choices=[
        'data_processing', 'graph_construction', 'community_detection', 
        'summarization', 'query_processing'
    ], help='Run a specific pipeline step')
    group.add_argument('--query', action='store_true',
                      help='Start interactive query system')
    
    args = parser.parse_args()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found!")
        print("Please create a .env file with your AWS credentials:")
        print("AWS_ACCESS_KEY_ID=your_key")
        print("AWS_SECRET_ACCESS_KEY=your_secret")
        print("REGION_NAME=us-east-1")
        sys.exit(1)
    
    # Run based on arguments
    if args.pipeline:
        run_full_pipeline()
    elif args.query:
        run_query_processing()
    elif args.step == 'data_processing':
        run_data_processing()
    elif args.step == 'graph_construction':
        run_graph_construction()
    elif args.step == 'community_detection':
        run_community_detection()
    elif args.step == 'summarization':
        run_community_summarization()
    elif args.step == 'query_processing':
        run_query_processing()

if __name__ == "__main__":
    main()
