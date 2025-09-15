# SimpleKG - Local to Global GraphRAG Implementation

A complete implementation of Microsoft's Local to Global GraphRAG approach for medical knowledge extraction and querying, built with Python, Neo4j, and AWS Bedrock.

## 🏗️ Architecture

This project implements the full GraphRAG pipeline:

```
Raw Medical Data → Entity Extraction → Knowledge Graph → Community Detection → Summarization → Query System
```

### Pipeline Components

1. **Data Processing** (`src/dataprocessing/`)
   - Text chunking and preprocessing
   - Entity and relationship extraction using AWS Bedrock Claude

2. **Graph Construction** (`src/graph_construction/`)
   - Neo4j knowledge graph creation
   - Entity and relationship storage

3. **Community Detection** (`src/community_detection/`)
   - Semantic similarity-based clustering
   - Medical specialty classification

4. **Summarization** (`src/summarisation/`)
   - LLM-powered community summaries
   - Medical context generation

5. **Query Processing** (`src/query_processing/`)
   - Local and global query routing
   - Interactive medical Q&A system

## 📁 Project Structure

```
simplekg/
├── main.py                          # Main pipeline orchestrator
├── .env                            # Environment variables (AWS credentials)
├── README.md                       # This file
│
├── src/                            # Source code
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── prompts.py              # LLM prompts for entity extraction
│   ├── dataprocessing/
│   │   ├── __init__.py
│   │   ├── data_processing.py      # Text chunking and preprocessing
│   │   └── er_extraction.py       # Entity-relationship extraction
│   ├── graph_construction/
│   │   ├── __init__.py
│   │   └── graph_construction.py   # Neo4j graph building
│   ├── community_detection/
│   │   ├── __init__.py
│   │   └── community_detection.py  # Semantic community detection
│   ├── summarisation/
│   │   ├── __init__.py
│   │   └── community_summarisation.py # LLM community summaries
│   └── query_processing/
│       ├── __init__.py
│       └── query_processing.py     # Local/Global query system
│
├── data/                           # Data storage
│   ├── raw/                        # Original medical texts
│   ├── processed/                  # Processed chunks and extractions
│   └── graphs/                     # Graph outputs and community data
│
├── mimic_ex_500/                   # Sample medical reports
│   └── report_*.txt                # Individual medical reports
│
└── reference/                      # Reference materials
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** with required packages:
   ```bash
   pip install neo4j langchain-aws boto3 python-dotenv scikit-learn numpy
   ```

2. **Neo4j Database** (choose one):
   - Neo4j Desktop with password `password`
   - Docker: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest`

3. **AWS Bedrock Access** with Claude model permissions

### Setup

1. **Clone and setup environment**:
   ```bash
   git clone <repository>
   cd simplekg
   ```

2. **Configure AWS credentials** in `.env`:
   ```env
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   REGION_NAME=us-east-1
   ```

3. **Start Neo4j** and ensure it's running on `bolt://localhost:7687`

### Running the Pipeline

#### Option 1: Complete Pipeline
```bash
python main.py --pipeline
```

#### Option 2: Individual Steps
```bash
# Step 1: Process data and extract entities
python main.py --step data_processing

# Step 2: Build knowledge graph
python main.py --step graph_construction

# Step 3: Detect communities
python main.py --step community_detection

# Step 4: Generate summaries
python main.py --step summarization

# Step 5: Query system
python main.py --step query_processing
```

#### Option 3: Interactive Queries Only
```bash
python main.py --query
```

## 🔍 Query Examples

The system supports both **Local** (entity-specific) and **Global** (community-based) queries:

### Local Queries
- "What is cirrhosis?"
- "What medications treat liver disease?"
- "Describe ventral hernia symptoms"

### Global Queries  
- "What are the main medical specialties?"
- "Give me an overview of laboratory values"
- "Compare different treatment approaches"

## 📊 Output Files

After running the pipeline, check these locations:

### Data Files
- `data/processed/processed_chunks.json` - Text chunks
- `data/processed/entity_extractions_50.json` - Extracted entities/relationships

### Graph Files
- `data/graphs/simple_communities_assignments.json` - Entity-to-community mapping
- `data/graphs/simple_communities_stats.json` - Community statistics
- `data/graphs/simple_communities_summaries.json` - Community summaries
- `data/graphs/community_summaries_detailed.json` - Detailed LLM summaries

### Neo4j Browser
Visit `http://localhost:7474` to visualize the knowledge graph and communities.

## 🏥 Medical Specialties Detected

The system automatically classifies entities into medical specialties:

- **Cardiology** - Heart, cardiac conditions, hypertension
- **Gastroenterology** - Liver, GI tract, hernias, cirrhosis  
- **Orthopedics** - Bones, joints, hip/knee replacements
- **Pharmacology** - Medications, treatments, dosages
- **Laboratory Medicine** - Lab values, blood tests, cultures
- **Pulmonology** - Lungs, respiratory conditions
- **Nephrology** - Kidneys, renal failure, dialysis
- **Endocrinology** - Diabetes, hormones, insulin
- **Hematology** - Blood disorders, anemia, coagulation
- **Neurology** - Brain, neurological conditions
- **Infectious Disease** - Infections, antibiotics, sepsis

## 🛠️ Technical Details

### Entity Types
- `CONDITION` - Medical conditions and diseases
- `MEDICATION` - Drugs and treatments  
- `LAB_VALUE` - Laboratory test results
- `PROCEDURE` - Medical procedures
- `ANATOMY` - Anatomical structures
- `UNKNOWN` - Unclassified entities

### Relationship Types
- `HAS_CONDITION` - Patient has condition
- `TREATS` - Medication treats condition
- `SHOWS` - Test shows result
- `PRESCRIBED` - Medication prescribed
- `LOCATED_IN` - Anatomical location
- `RELATES` - General medical relationship

### Community Detection
Uses semantic similarity with TF-IDF vectorization and hierarchical clustering to group related medical entities into meaningful communities.

## 🔧 Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   ```bash
   # Check if Neo4j is running
   docker ps  # or check Neo4j Desktop
   ```

2. **AWS Bedrock Access Denied**
   - Verify AWS credentials in `.env`
   - Ensure Bedrock model access in AWS console

3. **Import Errors**
   - Ensure all packages are installed
   - Check Python path includes `src/`

4. **Empty Results**
   - Verify input data in `mimic_ex_500/` or `data/raw/`
   - Check entity extraction outputs

### Performance Tips

- Start with small datasets for testing
- Use `max_chunks` parameter in entity extraction
- Monitor Neo4j memory usage for large graphs
- Consider batch processing for large datasets

## 📈 Extending the System

### Adding New Data Sources
1. Place raw text files in `data/raw/`
2. Update `data_processing.py` for new formats
3. Adjust entity extraction prompts if needed

### Custom Entity Types
1. Modify `src/config/prompts.py`
2. Update entity type classifications
3. Adjust community detection keywords

### New Medical Specialties
1. Add specialty keywords in `community_detection.py`
2. Update specialty classification logic
3. Test with domain-specific data

## 📚 References

- [Microsoft GraphRAG Paper](https://arxiv.org/abs/2404.16130)
- [Neo4j Graph Database](https://neo4j.com/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangChain Framework](https://langchain.com/)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Neo4j and AWS Bedrock documentation
3. Open an issue with detailed error messages and steps to reproduce
