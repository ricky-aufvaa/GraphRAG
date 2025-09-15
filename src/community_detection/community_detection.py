import json
from neo4j import GraphDatabase
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def connect_to_neo4j():
    """Connect to Neo4j database"""
    try:
        driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1 as test")
        print("✅ Connected to Neo4j successfully!")
        return driver
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        print("\n💡 Make sure Neo4j is running and has data loaded")
        return None

def get_graph_data(driver):
    """Extract graph data from Neo4j for community detection"""
    
    print("🔄 Extracting graph data from Neo4j...")
    
    entities = {}
    relationships = []
    
    with driver.session() as session:
        # Get all entities
        result = session.run("""
            MATCH (e:Entity)
            RETURN e.name as name, e.type as type, e.description as description
        """)
        
        for record in result:
            entities[record['name']] = {
                'type': record['type'],
                'description': record['description']
            }
        
        # Get all relationships
        result = session.run("""
            MATCH (source:Entity)-[r]->(target:Entity)
            RETURN source.name as source, target.name as target, 
                   type(r) as relationship, r.strength as strength
        """)
        
        for record in result:
            relationships.append({
                'source': record['source'],
                'target': record['target'],
                'relationship': record['relationship'],
                'strength': record.get('strength', 1.0)
            })
    
    print(f"✅ Extracted {len(entities)} entities and {len(relationships)} relationships")
    return entities, relationships

def semantic_community_detection(entities, relationships, n_clusters=15):
    """Semantic similarity-based community detection for medical entities"""
    
    print(f"🔍 Running semantic community detection (target: {n_clusters} communities)...")
    
    # Create text representations for each entity
    entity_texts = []
    entity_names = list(entities.keys())
    
    for entity_name in entity_names:
        entity_data = entities[entity_name]
        # Combine name, type, and description for rich text representation
        text = f"{entity_name} {entity_data['type']} {entity_data.get('description', '')}"
        entity_texts.append(text)
    
    # Create TF-IDF vectors
    print("📊 Creating TF-IDF vectors...")
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95
    )
    
    tfidf_matrix = vectorizer.fit_transform(entity_texts)
    
    # Add relationship-based features
    print("🔗 Adding relationship features...")
    
    # Create relationship adjacency matrix
    entity_to_idx = {name: idx for idx, name in enumerate(entity_names)}
    n_entities = len(entity_names)
    
    # Relationship type features
    rel_types = list(set(rel['relationship'] for rel in relationships))
    rel_features = np.zeros((n_entities, len(rel_types)))
    
    for rel in relationships:
        if rel['source'] in entity_to_idx and rel['target'] in entity_to_idx:
            source_idx = entity_to_idx[rel['source']]
            target_idx = entity_to_idx[rel['target']]
            rel_type_idx = rel_types.index(rel['relationship'])
            
            # Add relationship features for both entities
            rel_features[source_idx, rel_type_idx] += 1
            rel_features[target_idx, rel_type_idx] += 1
    
    # Combine TF-IDF and relationship features
    combined_features = np.hstack([tfidf_matrix.toarray(), rel_features])
    
    # Perform hierarchical clustering
    print("🎯 Performing hierarchical clustering...")
    
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        linkage='ward'
    )
    
    cluster_labels = clustering.fit_predict(combined_features)
    
    # Create communities
    communities = defaultdict(list)
    for idx, label in enumerate(cluster_labels):
        communities[label].append(entity_names[idx])
    
    # Convert to our format
    final_communities = {}
    for comm_id, entity_list in communities.items():
        final_communities[comm_id] = {
            'entities': entity_list,
            'size': len(entity_list)
        }
    
    print(f"✅ Created {len(final_communities)} semantic communities")
    
    # Calculate silhouette score for quality assessment
    try:
        from sklearn.metrics import silhouette_score
        silhouette = silhouette_score(combined_features, cluster_labels)
        print(f"📈 Silhouette score: {silhouette:.4f}")
    except:
        silhouette = 0.0
    
    return final_communities, silhouette

def analyze_communities(communities, entities, relationships):
    """Analyze community characteristics"""
    
    print("📊 Analyzing community characteristics...")
    
    community_stats = {}
    
    for comm_id, community in communities.items():
        entity_names = community['entities']
        
        # Count relationship types within community
        internal_relationships = defaultdict(int)
        external_relationships = defaultdict(int)
        
        for rel in relationships:
            source_in_comm = rel['source'] in entity_names
            target_in_comm = rel['target'] in entity_names
            
            if source_in_comm and target_in_comm:
                internal_relationships[rel['relationship']] += 1
            elif source_in_comm or target_in_comm:
                external_relationships[rel['relationship']] += 1
        
        # Determine most common entity type in community
        type_counts = defaultdict(int)
        for entity_name in entity_names:
            entity_type = entities.get(entity_name, {}).get('type', 'UNKNOWN')
            type_counts[entity_type] += 1
        
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else 'MIXED'
        
        # Determine medical specialty based on entities
        specialty = determine_medical_specialty(entity_names, entities)
        theme = generate_community_theme(entity_names, entities)
        
        community_stats[comm_id] = {
            'id': str(comm_id),
            'size': community['size'],
            'type': most_common_type,
            'specialty': specialty,
            'theme': theme,
            'entities': entity_names,
            'internal_relationships': dict(internal_relationships),
            'external_relationships': dict(external_relationships),
            'density': len(internal_relationships) / max(1, community['size'] * (community['size'] - 1) / 2),
            'type_distribution': dict(type_counts)
        }
    
    return community_stats

def determine_medical_specialty(entity_names, entities):
    """Determine medical specialty based on entity content"""
    
    # Enhanced medical specialty keywords
    specialties = {
        'Cardiology': ['heart', 'cardiac', 'aortic', 'hypertension', 'ejection fraction', 'valve', 'coronary', 'myocardial', 'arrhythmia'],
        'Gastroenterology': ['liver', 'hepatic', 'cirrhosis', 'abdomen', 'hernia', 'ascites', 'bowel', 'intestine', 'gastric', 'colon', 'gi', 'endoscopy'],
        'Orthopedics': ['hip', 'knee', 'bone', 'joint', 'replacement', 'osteoporosis', 'fracture', 'orthopedic', 'prosthesis'],
        'Pharmacology': ['medication', 'drug', 'treatment', 'therapy', 'prescription', 'dose', 'mg', 'administration'],
        'Laboratory Medicine': ['lab', 'test', 'value', 'anion gap', 'levels', 'blood', 'urine', 'serum', 'plasma', 'culture'],
        'Pulmonology': ['lung', 'pulmonary', 'respiratory', 'sarcoidosis', 'breathing', 'oxygen', 'ventilation'],
        'Nephrology': ['kidney', 'renal', 'failure', 'dialysis', 'creatinine', 'urinary', 'nephro'],
        'Endocrinology': ['insulin', 'diabetes', 'hormone', 'dextrose', 'glucose', 'thyroid', 'endocrine'],
        'Hematology': ['blood', 'anemia', 'platelet', 'hemoglobin', 'coagulation', 'hematocrit', 'leukocyte'],
        'Neurology': ['brain', 'neurological', 'seizure', 'stroke', 'neuro', 'cognitive'],
        'Infectious Disease': ['infection', 'antibiotic', 'sepsis', 'fever', 'culture', 'bacterial', 'viral']
    }
    
    specialty_scores = defaultdict(int)
    
    for entity_name in entity_names:
        entity_data = entities.get(entity_name, {})
        text_to_check = f"{entity_name} {entity_data.get('description', '')}".lower()
        
        for specialty, keywords in specialties.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    specialty_scores[specialty] += 1
    
    if specialty_scores:
        return max(specialty_scores.items(), key=lambda x: x[1])[0]
    else:
        return "General Medicine"

def generate_community_theme(entity_names, entities):
    """Generate a descriptive theme for the community"""
    
    # Count entity types
    type_counts = defaultdict(int)
    for entity_name in entity_names:
        entity_type = entities.get(entity_name, {}).get('type', 'UNKNOWN')
        type_counts[entity_type] += 1
    
    # Generate theme based on most common types and entities
    if type_counts['CONDITION'] > 0:
        conditions = [name for name in entity_names 
                     if entities.get(name, {}).get('type') == 'CONDITION']
        if any('heart' in name or 'cardiac' in name or 'aortic' in name 
               for name in conditions):
            return "Cardiovascular conditions and treatments"
        elif any('liver' in name or 'hepatic' in name or 'cirrhosis' in name 
                 for name in conditions):
            return "Liver diseases and complications"
        elif any('hip' in name or 'knee' in name or 'bone' in name 
                 for name in conditions):
            return "Orthopedic conditions and procedures"
        elif any('blood' in name or 'anemia' in name or 'hemoglobin' in name
                 for name in conditions):
            return "Hematological conditions and blood disorders"
        else:
            return f"Medical conditions ({len(conditions)} conditions)"
    
    elif type_counts['MEDICATION'] > 0:
        return f"Medications and treatments ({type_counts['MEDICATION']} medications)"
    
    elif type_counts['ANATOMY'] > 0:
        return f"Anatomical structures ({type_counts['ANATOMY']} structures)"
    
    elif type_counts['LAB_VALUE'] > 0:
        return f"Laboratory values and tests ({type_counts['LAB_VALUE']} lab values)"
    
    elif type_counts['PROCEDURE'] > 0:
        return f"Medical procedures ({type_counts['PROCEDURE']} procedures)"
    
    else:
        return f"Mixed medical entities ({len(entity_names)} entities)"

def clear_existing_communities(driver):
    """Clear existing Community nodes and BELONGS_TO relationships"""
    with driver.session() as session:
        session.run("MATCH (c:Community) DETACH DELETE c")
    print("🧹 Cleared existing communities")

def save_communities_to_neo4j(driver, community_stats):
    """Save community information back to Neo4j"""
    
    print("💾 Saving communities to Neo4j...")
    
    with driver.session() as session:
        # Create Community nodes
        for comm_id, stats in community_stats.items():
            session.run("""
                CREATE (c:Community {
                    id: $id,
                    size: $size,
                    type: $type,
                    specialty: $specialty,
                    theme: $theme,
                    density: $density
                })
            """,
            id=stats['id'],
            size=stats['size'],
            type=stats['type'],
            specialty=stats['specialty'],
            theme=stats['theme'],
            density=stats['density'])
        
        # Create BELONGS_TO relationships
        for comm_id, stats in community_stats.items():
            for entity_name in stats['entities']:
                session.run("""
                    MATCH (e:Entity {name: $entity_name})
                    MATCH (c:Community {id: $community_id})
                    CREATE (e)-[:BELONGS_TO]->(c)
                """,
                entity_name=entity_name,
                community_id=stats['id'])
    
    print(f"✅ Saved {len(community_stats)} communities to Neo4j")

def save_community_files(community_stats, quality_score):
    """Save community data to JSON files"""
    
    print("💾 Saving community files...")
    
    # Ensure data/graphs directory exists
    import os
    os.makedirs('data/graphs', exist_ok=True)
    
    # Community assignments
    assignments = {}
    for comm_id, stats in community_stats.items():
        for entity in stats['entities']:
            assignments[entity] = int(stats['id'])
    
    with open('data/graphs/simple_communities_assignments.json', 'w') as f:
        json.dump(assignments, f, indent=2)
    
    # Community statistics with quality score
    stats_with_quality = {
        'silhouette_score': float(quality_score),
        'total_communities': len(community_stats),
        'communities': {str(k): v for k, v in community_stats.items()}
    }
    
    with open('data/graphs/simple_communities_stats.json', 'w') as f:
        json.dump(stats_with_quality, f, indent=2, default=str)
    
    # Community summaries
    summaries = {}
    for comm_id, stats in community_stats.items():
        summaries[stats['id']] = {
            'specialty': stats['specialty'],
            'theme': stats['theme'],
            'size': stats['size'],
            'type': stats['type'],
            'type_distribution': stats['type_distribution'],
            'sample_entities': stats['entities'][:5]  # First 5 entities
        }
    
    with open('data/graphs/simple_communities_summaries.json', 'w') as f:
        json.dump(summaries, f, indent=2)
    
    print("✅ Community files saved:")
    print("   - data/graphs/simple_communities_assignments.json")
    print("   - data/graphs/simple_communities_stats.json") 
    print("   - data/graphs/simple_communities_summaries.json")

def generate_community_queries():
    """Generate Neo4j queries for community visualization"""
    
    queries = {
        "1. All Communities (Semantic)": """
MATCH (c:Community)
RETURN c.id as CommunityID, c.specialty as Specialty, 
       c.size as Size, c.theme as Theme
ORDER BY c.size DESC
        """,
        
        "2. Communities with Entities (Hub View)": """
MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
RETURN c, e
        """,
        
        "3. Large Communities (Size >= 10)": """
MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
WHERE c.size >= 10
RETURN c, e
        """,
        
        "4. Medical Specialties Overview": """
MATCH (c:Community)
RETURN c.specialty as Specialty, 
       count(c) as Communities,
       sum(c.size) as TotalEntities,
       avg(c.size) as AvgSize
ORDER BY TotalEntities DESC
        """,
        
        "5. Cardiology Communities": """
MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
WHERE c.specialty = 'Cardiology'
RETURN c, e
        """,
        
        "6. Gastroenterology Communities": """
MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
WHERE c.specialty = 'Gastroenterology'
RETURN c, e
        """,
        
        "7. Inter-Community Connections": """
MATCH (c1:Community)<-[:BELONGS_TO]-(e1:Entity)-[r]-(e2:Entity)-[:BELONGS_TO]->(c2:Community)
WHERE c1.id <> c2.id
RETURN c1, e1, r, e2, c2
LIMIT 30
        """
    }
    
    print(f"\n🎨 SEMANTIC COMMUNITY VISUALIZATION QUERIES")
    print("="*60)
    print("Copy these into Neo4j Browser (http://localhost:7474):")
    
    for name, query in queries.items():
        print(f"\n{name}:")
        print("```cypher")
        print(query.strip())
        print("```")

def main():
    """Main function for semantic community detection"""
    
    print("🏥 SEMANTIC COMMUNITY DETECTION FOR NEO4J")
    print("="*60)
    print("🧠 Using semantic similarity for meaningful medical communities!")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        return
    
    try:
        # Extract graph data
        entities, relationships = get_graph_data(driver)
        
        if not entities:
            print("❌ No entities found in Neo4j. Run simple_neo4j.py first!")
            return
        
        # Clear existing communities
        clear_existing_communities(driver)
        
        # Test different numbers of clusters
        cluster_options = [10, 15, 20, 25]
        best_communities = None
        best_quality = -1
        best_n_clusters = 15
        
        print(f"\n🔍 Testing different numbers of clusters...")
        
        for n_clusters in cluster_options:
            communities, quality = semantic_community_detection(entities, relationships, n_clusters)
            avg_size = sum(c['size'] for c in communities.values()) / len(communities)
            print(f"   {n_clusters} clusters: quality={quality:.4f}, avg_size={avg_size:.1f}")
            
            # Prefer solutions with good quality and reasonable community sizes
            if quality > best_quality and avg_size > 5:
                best_communities = communities
                best_quality = quality
                best_n_clusters = n_clusters
        
        print(f"\n🏆 Best result: {best_n_clusters} clusters with quality score {best_quality:.4f}")
        
        # Analyze communities
        community_stats = analyze_communities(best_communities, entities, relationships)
        
        # Display results
        print(f"\n📊 SEMANTIC COMMUNITY DETECTION RESULTS:")
        print(f"   - Total communities: {len(community_stats)}")
        print(f"   - Quality score: {best_quality:.4f}")
        print(f"   - Optimal clusters: {best_n_clusters}")
        
        # Show all communities
        sorted_communities = sorted(community_stats.items(), 
                                  key=lambda x: x[1]['size'], reverse=True)
        
        print(f"\n🏷️  ALL COMMUNITIES:")
        for i, (comm_id, stats) in enumerate(sorted_communities):
            print(f"\n   Community {stats['id']} ({stats['size']} entities):")
            print(f"   - Specialty: {stats['specialty']}")
            print(f"   - Theme: {stats['theme']}")
            print(f"   - Main type: {stats['type']}")
            print(f"   - Sample entities: {', '.join(stats['entities'][:5])}")
        
        # Save to Neo4j
        save_communities_to_neo4j(driver, community_stats)
        
        # Save to files
        save_community_files(community_stats, best_quality)
        
        # Generate queries
        generate_community_queries()
        
        print(f"\n🎉 SUCCESS!")
        print(f"="*40)
        print(f"✅ Created {len(community_stats)} meaningful medical communities")
        print(f"📈 Quality score: {best_quality:.4f}")
        print(f"🌐 Open Neo4j Browser: http://localhost:7474")
        print(f"📊 Use the community queries above for visualization")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.close()
        print("\n🔌 Neo4j connection closed")

if __name__ == "__main__":
    main()
