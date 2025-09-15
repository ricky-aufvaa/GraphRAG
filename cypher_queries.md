# GraphRAG Visualization Cypher Queries

## Complete GraphRAG Visualization

MATCH (c:Community)<-[belongs:BELONGS_TO]-(e:Entity)
WHERE c.id IN ["0", "1","2","3","4","5","6","7"]
OPTIONAL MATCH (e)-[r]-(connected:Entity)
RETURN c, belongs, e, r, connected

### 1. Full GraphRAG Structure (Communities → Entities → Relationships)
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c, e1, r, e2
```

### 2. Enhanced GraphRAG with Community Details
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c.id as CommunityID, 
       c.specialty as Specialty,
       c.theme as Theme,
       c.size as CommunitySize,
       e1, r, e2
ORDER BY c.size DESC
```

### 3. Multi-Level Entity Relationships (2 hops from communities)
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
OPTIONAL MATCH (e1)-[r1]-(e2:Entity)
OPTIONAL MATCH (e2)-[r2]-(e3:Entity)
WHERE e3 <> e1  // Avoid cycles back to original entity
RETURN c, e1, r1, e2, r2, e3
LIMIT 500
```

### 4. Community-Centric View with Entity Networks
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
MATCH (e1)-[r]-(e2:Entity)
RETURN c, e1, r, e2
ORDER BY c.size DESC
LIMIT 300
```

### 5. Large Communities with Rich Connections
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
WHERE c.size >= 10
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c, e1, r, e2
```

### 6. Medical Specialty Networks
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
WHERE c.specialty IN ['Gastroenterology', 'Cardiology', 'Pharmacology', 'Laboratory Medicine']
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c, e1, r, e2
```

### 7. Inter-Community Connections
```cypher
MATCH (c1:Community)<-[:BELONGS_TO]-(e1:Entity)-[r]-(e2:Entity)-[:BELONGS_TO]->(c2:Community)
WHERE c1.id <> c2.id
RETURN c1, e1, r, e2, c2
LIMIT 100
```

### 8. Complete Graph with Node Labels
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c.specialty + " (Community " + c.id + ")" as CommunityLabel,
       e1.name + " (" + e1.type + ")" as Entity1Label,
       type(r) as RelationshipType,
       e2.name + " (" + e2.type + ")" as Entity2Label,
       c, e1, r, e2
```

## Focused Visualizations

### 9. Two Communities with Their Entity Networks
```cypher
MATCH (c1:Community)<-[:BELONGS_TO]-(e1:Entity)
MATCH (c2:Community)<-[:BELONGS_TO]-(e2:Entity)
WHERE c1.id <> c2.id
WITH c1, c2, collect(e1) as entities1, collect(e2) as entities2
ORDER BY c1.size DESC, c2.size DESC
LIMIT 1

UNWIND entities1 as entity1
UNWIND entities2 as entity2
MATCH (c1)<-[:BELONGS_TO]-(entity1)
MATCH (c2)<-[:BELONGS_TO]-(entity2)
OPTIONAL MATCH (entity1)-[r1]-(connected1:Entity)
OPTIONAL MATCH (entity2)-[r2]-(connected2:Entity)
RETURN c1, entity1, r1, connected1, c2, entity2, r2, connected2
```

### 10. Two Specific Communities (Gastroenterology & Cardiology)
```cypher
MATCH (c1:Community {specialty: 'Gastroenterology'})<-[:BELONGS_TO]-(e1:Entity)
MATCH (c2:Community {specialty: 'Cardiology'})<-[:BELONGS_TO]-(e2:Entity)
OPTIONAL MATCH (e1)-[r1]-(connected1:Entity)
OPTIONAL MATCH (e2)-[r2]-(connected2:Entity)
RETURN c1, e1, r1, connected1, c2, e2, r2, connected2
LIMIT 100
```

### 11. Two Largest Communities with Entity Relationships
```cypher
MATCH (c:Community)
WITH c ORDER BY c.size DESC LIMIT 2
MATCH (c)<-[:BELONGS_TO]-(e:Entity)
OPTIONAL MATCH (e)-[r]-(connected:Entity)
RETURN c, e, r, connected
```

### 12. Condition-Medication Networks by Community
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(condition:Entity {type: 'CONDITION'})
MATCH (condition)-[r]-(medication:Entity {type: 'MEDICATION'})
RETURN c, condition, r, medication
```

### 10. High-Density Communities (Most Connected)
```cypher
MATCH (c:Community)<-[:BELONGS_TO]-(e1:Entity)
WITH c, count(e1) as entityCount
WHERE entityCount >= 15
MATCH (c)<-[:BELONGS_TO]-(e1:Entity)
OPTIONAL MATCH (e1)-[r]-(e2:Entity)
RETURN c, e1, r, e2
```

## Usage Instructions

1. **Open Neo4j Browser**: Go to http://localhost:7474
2. **Login**: Username: `neo4j`, Password: `password`
3. **Copy and paste** any of the above queries
4. **Click Run** to visualize

## Recommended Queries for Different Views

- **Start with Query #1** for the complete overview
- **Use Query #5** for cleaner visualization (large communities only)
- **Try Query #6** for specific medical specialties
- **Use Query #7** to see how communities connect to each other

## Visualization Tips

- **Limit results** if the graph becomes too crowded (add `LIMIT 200` at the end)
- **Filter by specialty** to focus on specific medical areas
- **Use the Neo4j Browser controls** to:
  - Zoom in/out with mouse wheel
  - Drag nodes to reorganize
  - Click on nodes/relationships to see properties
  - Use the style panel to change colors and sizes

## Color Coding Suggestions

In Neo4j Browser, you can customize colors:
- **Communities**: Large blue nodes
- **CONDITION entities**: Red nodes
- **MEDICATION entities**: Green nodes
- **LAB_VALUE entities**: Yellow nodes
- **PROCEDURE entities**: Purple nodes
- **ANATOMY entities**: Orange nodes
