# Simple GraphRAG Query System - No Classes!
# This answers medical questions using the knowledge graph and communities

import json
import boto3
from langchain_aws import ChatBedrock
from dotenv import load_dotenv
import os
load_dotenv()

# AWS Bedrock setup
def setup_bedrock():
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name = os.getenv("REGION_NAME")
    )

    llm = ChatBedrock(
        client=bedrock_client,
        region_name = os.getenv("REGION_NAME"),
        model_id = "anthropic.claude-3-haiku-20240307-v1:0",
        model_kwargs = {
            "max_tokens":4500,
            "temperature":0.1
        }
    )
    return llm

# Load all the data we need
def load_all_data():
    """Load all the GraphRAG data"""
    
    print("🔄 Loading GraphRAG data...")
    
    # Load graph data
    with open('data/graphs/simple_medical_graph.json', 'r') as f:
        graph_data = json.load(f)
    
    # Load community data
    with open('data/graphs/simple_communities_assignments.json', 'r') as f:
        community_assignments = json.load(f)
    
    with open('data/graphs/simple_communities_stats.json', 'r') as f:
        community_stats_data = json.load(f)
        community_stats = community_stats_data.get('communities', {})
    
    with open('data/graphs/simple_communities_summaries.json', 'r') as f:
        community_summaries = json.load(f)
    
    print("✅ All data loaded successfully")
    
    return graph_data, community_assignments, community_stats, community_summaries

def determine_query_type(question):
    """Determine if this should be a local or global query"""
    
    question_lower = question.lower()
    
    # Global query keywords
    global_keywords = [
        'overview', 'summary', 'all', 'total', 'overall', 'general',
        'what are', 'list', 'types of', 'categories', 'compare',
        'difference between', 'how many', 'specialties'
    ]
    
    # Local query keywords
    local_keywords = [
        'what is', 'define', 'explain', 'describe', 'symptoms of',
        'treatment for', 'diagnosis of', 'causes of', 'specific'
    ]
    
    # Count keyword matches
    global_score = sum(1 for keyword in global_keywords if keyword in question_lower)
    local_score = sum(1 for keyword in local_keywords if keyword in question_lower)
    
    if global_score > local_score:
        return "global"
    elif local_score > 0:
        return "local"
    else:
        return "global"  # Default to global

def find_entities_in_question(question, graph_data):
    """Find medical entities mentioned in the question"""
    
    question_lower = question.lower()
    found_entities = []
    
    # Search through all entities
    for node in graph_data['nodes']:
        entity_name = node['name'].lower()
        
        # Check if entity name is in the question
        if entity_name in question_lower:
            found_entities.append(node)
    
    return found_entities[:5]  # Return top 5 matches

def get_entity_neighbors(entity_id, graph_data):
    """Get entities connected to a specific entity"""
    
    neighbors = []
    
    # Find all edges connected to this entity
    for edge in graph_data['edges']:
        if edge['source'] == entity_id:
            # Find the target entity
            for node in graph_data['nodes']:
                if node['id'] == edge['target']:
                    neighbors.append({
                        'entity': node,
                        'relationship': edge['relationship'],
                        'description': edge['description']
                    })
        elif edge['target'] == entity_id:
            # Find the source entity
            for node in graph_data['nodes']:
                if node['id'] == edge['source']:
                    neighbors.append({
                        'entity': node,
                        'relationship': edge['relationship'],
                        'description': edge['description']
                    })
    
    return neighbors[:10]  # Return top 10 neighbors

def find_relevant_communities(question, community_summaries):
    """Find communities relevant to the question"""
    
    question_lower = question.lower()
    relevant_communities = []
    
    # Search through community summaries
    for comm_id, summary in community_summaries.items():
        theme = summary.get('theme', '').lower()
        specialty = summary.get('specialty', '').lower()
        
        # Check if question words appear in theme or specialty
        question_words = question_lower.split()
        for word in question_words:
            if len(word) > 3 and (word in theme or word in specialty):
                relevant_communities.append(comm_id)
                break
    
    return relevant_communities[:5]  # Return top 5 communities

def answer_local_query(question, graph_data, community_assignments, community_stats, community_summaries, llm):
    """Answer a local (entity-specific) query"""
    
    print("🎯 Answering LOCAL query...")
    
    # Find entities mentioned in the question
    entities = find_entities_in_question(question, graph_data)
    
    if not entities:
        return "I couldn't find specific medical entities in your question. Please be more specific about conditions, medications, or procedures."
    
    # Display found entities
    print(f"\n🔍 FOUND ENTITIES ({len(entities)}):")
    for i, entity in enumerate(entities, 1):
        print(f"   {i}. {entity['name']} ({entity['type']})")
        if entity.get('description'):
            print(f"      Description: {entity['description']}")
    
    # Get information about each entity
    entity_info = []
    all_relationships = []
    all_communities = set()
    
    for entity in entities:
        # Get neighbors
        neighbors = get_entity_neighbors(entity['id'], graph_data)
        
        # Collect relationships
        for neighbor in neighbors:
            all_relationships.append({
                'source': entity['name'],
                'target': neighbor['entity']['name'],
                'relationship': neighbor['relationship'],
                'description': neighbor.get('description', '')
            })
        
        # Get community info
        community_id = community_assignments.get(entity['name'], 'unknown')
        community_summary = community_summaries.get(community_id, {})
        all_communities.add(community_id)
        
        entity_info.append({
            'entity': entity,
            'neighbors': neighbors,
            'community': community_summary.get('specialty', 'Unknown specialty'),
            'community_id': community_id
        })
    
    # Display relationships
    if all_relationships:
        print(f"\n🔗 RELEVANT RELATIONSHIPS ({len(all_relationships)}):")
        for i, rel in enumerate(all_relationships[:10], 1):  # Show top 10
            print(f"   {i}. {rel['source']} --[{rel['relationship']}]--> {rel['target']}")
            if rel['description']:
                print(f"      Description: {rel['description']}")
        if len(all_relationships) > 10:
            print(f"   ... and {len(all_relationships) - 10} more relationships")
    
    # Display communities
    if all_communities and 'unknown' not in all_communities:
        print(f"\n🏘️ RELEVANT COMMUNITIES ({len(all_communities)}):")
        for i, comm_id in enumerate(sorted(all_communities), 1):
            if comm_id in community_summaries:
                comm_info = community_summaries[comm_id]
                specialty = comm_info.get('specialty', 'Unknown')
                theme = comm_info.get('theme', 'No theme')
                print(f"   {i}. Community {comm_id}: {specialty}")
                print(f"      Theme: {theme}")
    
    print(f"\n💡 ANSWER:")
    
    # Generate answer
    if llm:
        return generate_llm_local_answer(question, entity_info, llm)
    else:
        return generate_simple_local_answer(question, entity_info)

def answer_global_query(question, community_stats, community_summaries, llm):
    """Answer a global (community-based) query"""
    
    print("🌐 Answering GLOBAL query...")
    
    # Find relevant communities
    relevant_communities = find_relevant_communities(question, community_summaries)
    
    if not relevant_communities:
        # Use all communities for very general questions
        relevant_communities = list(community_summaries.keys())[:10]
        print(f"\n🔍 Using all available communities (top 10)")
    else:
        print(f"\n🔍 Found {len(relevant_communities)} relevant communities")
    
    # Get community information
    community_info = []
    for comm_id in relevant_communities:
        if comm_id in community_summaries and comm_id in community_stats:
            community_info.append({
                'id': comm_id,
                'summary': community_summaries[comm_id],
                'stats': community_stats[comm_id]
            })
    
    # Display relevant communities
    if community_info:
        print(f"\n🏘️ RELEVANT COMMUNITIES ({len(community_info)}):")
        for i, info in enumerate(community_info, 1):
            summary = info['summary']
            stats = info['stats']
            specialty = summary.get('specialty', 'Unknown')
            theme = summary.get('theme', 'No theme')
            size = stats.get('size', 0)
            
            print(f"   {i}. Community {info['id']}: {specialty} ({size} entities)")
            print(f"      Theme: {theme}")
            
            # Show sample entities if available
            if summary.get('sample_entities'):
                entities = summary['sample_entities'][:3]  # Show first 3
                print(f"      Sample entities: {', '.join(entities)}")
    
    print(f"\n💡 ANSWER:")
    
    # Generate answer
    if llm:
        return generate_llm_global_answer(question, community_info, llm)
    else:
        return generate_simple_global_answer(question, community_info)

def generate_llm_local_answer(question, entity_info, llm):
    """Generate answer using LLM for local queries"""
    
    # Prepare context
    context = "Medical Entity Information:\n\n"
    
    for i, info in enumerate(entity_info):
        entity = info['entity']
        context += f"Entity {i+1}: {entity['name']} ({entity['type']})\n"
        context += f"Description: {entity['description']}\n"
        context += f"Medical Specialty: {info['community']}\n"
        
        if info['neighbors']:
            context += "Related entities:\n"
            for neighbor in info['neighbors'][:5]:
                neighbor_entity = neighbor['entity']
                context += f"  - {neighbor_entity['name']} ({neighbor_entity['type']}) via {neighbor['relationship']}\n"
        context += "\n"
    
    # Create prompt
    prompt = f"""
    You are a medical expert. Answer the following question using the provided medical entity information.
    
    Question: {question}
    
    {context}
    
    Provide a comprehensive, medically accurate answer based on the entity relationships and context provided.
    Focus on clinical relevance and practical implications.
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"⚠️  LLM failed: {e}")
        return generate_simple_local_answer(question, entity_info)

def generate_llm_global_answer(question, community_info, llm):
    """Generate answer using LLM for global queries"""
    
    # Prepare context
    context = "Medical Community Information:\n\n"
    
    for info in community_info:
        summary = info['summary']
        stats = info['stats']
        
        context += f"Community {info['id']} ({summary.get('specialty', 'Unknown')}):\n"
        context += f"Size: {stats['size']} entities\n"
        context += f"Theme: {summary.get('theme', 'No theme')}\n"
        context += f"Key entities: {', '.join(summary.get('key_entities', [])[:5])}\n\n"
    
    # Create prompt
    prompt = f"""
    You are a medical expert. Answer the following question using the provided medical community information.
    
    Question: {question}
    
    {context}
    
    Provide a comprehensive answer that synthesizes information across medical specialties.
    Focus on providing a broad medical perspective and clinical insights.
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"⚠️  LLM failed: {e}")
        return generate_simple_global_answer(question, community_info)

def generate_simple_local_answer(question, entity_info):
    """Generate simple rule-based answer for local queries"""
    
    answer = "Based on the medical knowledge graph:\n\n"
    
    for info in entity_info:
        entity = info['entity']
        answer += f"**{entity['name']}** ({entity['type']}):\n"
        
        if entity['description']:
            answer += f"- Description: {entity['description']}\n"
        
        answer += f"- Medical specialty: {info['community']}\n"
        
        if info['neighbors']:
            neighbor_names = [n['entity']['name'] for n in info['neighbors'][:5]]
            answer += f"- Related to: {', '.join(neighbor_names)}\n"
        
        answer += "\n"
    
    return answer

def generate_simple_global_answer(question, community_info):
    """Generate simple rule-based answer for global queries"""
    
    answer = "Based on the medical knowledge communities:\n\n"
    
    for info in community_info:
        summary = info['summary']
        stats = info['stats']
        
        answer += f"**{summary.get('specialty', 'Unknown Specialty')}** (Community {info['id']}):\n"
        answer += f"- {summary.get('theme', 'No theme available')}\n"
        answer += f"- Size: {stats['size']} entities\n"
        
        if summary.get('key_entities'):
            answer += f"- Key concepts: {', '.join(summary['key_entities'][:5])}\n"
        
        answer += "\n"
    
    return answer

def query_medical_knowledge(question):
    """Main function to answer a medical question"""
    
    print(f"\n🔍 MEDICAL QUERY: {question}")
    print("="*60)
    
    # Load data
    graph_data, community_assignments, community_stats, community_summaries = load_all_data()
    
    # Set up LLM
    llm = setup_bedrock()
    
    # Determine query type
    query_type = determine_query_type(question)
    print(f"📊 Query Type: {query_type.upper()}")
    
    # Answer the question
    if query_type == "local":
        answer = answer_local_query(question, graph_data, community_assignments, 
                                  community_stats, community_summaries, llm)
    else:
        answer = answer_global_query(question, community_stats, community_summaries, llm)
    
    return answer, query_type

# Main interactive function
def main():
    """Main interactive query system"""
    
    print("🏥 SIMPLE MEDICAL GRAPHRAG QUERY SYSTEM")
    print("="*50)
    

    
    # Interactive mode
    print(f"\n🎮 INTERACTIVE MODE")
    print("Type your medical questions, or 'quit' to exit")
    
    while True:
        try:
            question = input("\n❓ Enter your medical question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            elif not question:
                continue
            
            # Answer the question
            answer, query_type = query_medical_knowledge(question)
            
            print(f"\n💡 Answer ({query_type} query):")
            print(answer)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Thank you for using the Medical GraphRAG Query System!")

if __name__ == "__main__":
    main()
