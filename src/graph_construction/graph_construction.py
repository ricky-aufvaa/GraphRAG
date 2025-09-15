import json
from neo4j import GraphDatabase

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
        print("\n💡 Make sure Neo4j is running:")
        print("1. Neo4j Desktop with password 'password'")
        print("2. Or Docker: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest")
        return None

def clear_database(driver):
    """Clear all existing data"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("🧹 Database cleared")

def create_indexes(driver):
    """Create indexes for better performance"""
    with driver.session() as session:
        try:
            session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
        except:
            pass  # Index already exists
        try:
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
        except:
            pass  # Index already exists
    print("📊 Indexes ready")

def load_entities_and_relationships(driver, json_file="data/processed/entity_extractions_50.json"):
    """Load entities and relationships from JSON into Neo4j"""
    
    print(f"🔄 Loading data from {json_file}...")
    
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    entities_created = 0
    relationships_created = 0
    
    with driver.session() as session:
        # Process each chunk in the JSON
        for chunk in data:
            # Create entities
            entities = chunk.get('entities', [])
            for entity in entities:
                session.run("""
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type,
                        e.description = $description
                """, 
                name=entity['name'],
                type=entity['type'],
                description=entity.get('description', ''))
                entities_created += 1
            
            # Create relationships
            relationships = chunk.get('relationships', [])
            for rel in relationships:
                # Create relationship with the exact relationship type from JSON
                session.run(f"""
                    MATCH (source:Entity {{name: $source_name}})
                    MATCH (target:Entity {{name: $target_name}})
                    CREATE (source)-[r:{rel['relationship']} {{
                        description: $description,
                        strength: $strength
                    }}]->(target)
                """,
                source_name=rel['source'],
                target_name=rel['target'],
                description=rel.get('description', ''),
                strength=rel.get('strength', 1.0))
                relationships_created += 1
    
    print(f"✅ Data loaded successfully!")
    print(f"   - Entities created: {entities_created}")
    print(f"   - Relationships created: {relationships_created}")
    
    return entities_created, relationships_created

def show_sample_data(driver):
    """Show sample data to verify loading"""
    print("\n🔍 SAMPLE DATA VERIFICATION:")
    
    with driver.session() as session:
        # Show entity counts by type
        result = session.run("""
            MATCH (e:Entity)
            RETURN e.type as entity_type, count(e) as count
            ORDER BY count DESC
        """)
        
        print("\n📊 Entity Types:")
        for record in result:
            print(f"   - {record['entity_type']}: {record['count']}")
        
        # Show relationship types
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
        """)
        
        print("\n🔗 Relationship Types:")
        for record in result:
            print(f"   - {record['relationship_type']}: {record['count']}")
        
        # Show sample relationships
        result = session.run("""
            MATCH (source:Entity)-[r]->(target:Entity)
            RETURN source.name as source, type(r) as relationship, target.name as target
            LIMIT 10
        """)
        
        print("\n🎯 Sample Relationships:")
        for record in result:
            print(f"   - {record['source']} ->[{record['relationship']}]-> {record['target']}")

def generate_visualization_queries():
    """Generate Cypher queries for Neo4j Browser visualization"""
    
    queries = {
        "1. Complete Graph": """
MATCH (n:Entity)-[r]->(m:Entity)
RETURN n, r, m
        """,
        
        "2. Ventral Hernia Connections": """
MATCH (vh:Entity {name: 'ventral hernia'})-[r]-(connected:Entity)
RETURN vh, r, connected
        """,
        
        "3. Conditions and Their Effects": """
MATCH (source:Entity {type: 'CONDITION'})-[r:AFFECTS]->(target:Entity)
RETURN source, r, target
        """,
        
        "4. Medications and Treatments": """
MATCH (med:Entity {type: 'MEDICATION'})-[r]-(condition:Entity {type: 'CONDITION'})
RETURN med, r, condition
        """,
        
        "5. Patient Conditions": """
MATCH (condition:Entity)-[r:HAS_CONDITION]->(patient:Entity {name: 'patient'})
RETURN condition, r, patient
        """,
        
        "6. Anatomical Relationships": """
MATCH (anat:Entity {type: 'ANATOMY'})-[r]-(other:Entity)
RETURN anat, r, other
        """,
        
        "7. High-Strength Relationships": """
MATCH (source:Entity)-[r]->(target:Entity)
WHERE r.strength >= 0.8
RETURN source, r, target
        """,
        
        "8. Specific Relationship: AFFECTS": """
MATCH (source:Entity)-[r:AFFECTS]->(target:Entity)
RETURN source, r, target
        """
    }
    
    print(f"\n🎨 NEO4J BROWSER VISUALIZATION QUERIES")
    print("="*60)
    print("Copy these queries into Neo4j Browser (http://localhost:7474):")
    
    for name, query in queries.items():
        print(f"\n{name}:")
        print("```cypher")
        print(query.strip())
        print("```")

def export_graph_to_json(driver, output_file="data/graphs/simple_medical_graph.json"):
    """Export the Neo4j graph to JSON format for query processing"""
    
    print(f"📤 Exporting graph to {output_file}...")
    
    # Ensure output directory exists
    import os
    os.makedirs('data/graphs', exist_ok=True)
    
    nodes = []
    edges = []
    
    with driver.session() as session:
        # Get all entities (nodes)
        result = session.run("""
            MATCH (e:Entity)
            RETURN e.name as name, e.type as type, e.description as description
        """)
        
        node_id_map = {}
        for i, record in enumerate(result):
            node_id = f"entity_{i}"
            node_id_map[record['name']] = node_id
            
            nodes.append({
                'id': node_id,
                'name': record['name'],
                'type': record['type'],
                'description': record['description'] or ''
            })
        
        # Get all relationships (edges)
        result = session.run("""
            MATCH (source:Entity)-[r]->(target:Entity)
            RETURN source.name as source_name, target.name as target_name,
                   type(r) as relationship, r.description as description,
                   r.strength as strength
        """)
        
        for record in result:
            source_id = node_id_map.get(record['source_name'])
            target_id = node_id_map.get(record['target_name'])
            
            if source_id and target_id:
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'relationship': record['relationship'],
                    'description': record['description'] or '',
                    'strength': record.get('strength', 1.0)
                })
    
    # Create graph JSON structure
    graph_data = {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'exported_at': str(datetime.now()) if 'datetime' in globals() else 'unknown'
        }
    }
    
    # Save to JSON file
    with open(output_file, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"✅ Exported {len(nodes)} nodes and {len(edges)} edges to {output_file}")
    return graph_data

def main():
    """Main function to load data into Neo4j"""
    
    print("🏥 SIMPLE NEO4J LOADER FOR MEDICAL ENTITIES")
    print("="*50)
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        return
    
    try:
        # Clear existing data
        clear_database(driver)
        
        # Create indexes
        create_indexes(driver)
        
        # Load entities and relationships
        entities, relationships = load_entities_and_relationships(driver)
        
        # Show sample data
        show_sample_data(driver)
        
        # Export graph to JSON for query processing
        export_graph_to_json(driver)
        
        # Generate visualization queries
        generate_visualization_queries()
        
        print(f"\n🎉 SUCCESS!")
        print(f"="*30)
        print(f"✅ Loaded {entities} entities and {relationships} relationships")
        print(f"📤 Exported graph data to data/graphs/simple_medical_graph.json")
        print(f"🌐 Open Neo4j Browser: http://localhost:7474")
        print(f"🔑 Username: neo4j, Password: password")
        print(f"📊 Use the queries above for visualization")
        print(f"\n🎯 Try this query to see ventral hernia connections:")
        print(f"MATCH (vh:Entity {{name: 'ventral hernia'}})-[r]-(connected:Entity)")
        print(f"RETURN vh, r, connected")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        driver.close()
        print("\n🔌 Neo4j connection closed")

if __name__ == "__main__":
    main()
