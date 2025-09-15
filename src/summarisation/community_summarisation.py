import json
import boto3
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
load_dotenv()

def connect_to_neo4j():
    """Connect to Neo4j database"""
    try:
        driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
        with driver.session() as session:
            session.run("RETURN 1 as test")
        print("✅ Connected to Neo4j successfully!")
        return driver
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        return None

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

def get_communities_from_neo4j(driver):
    """Get all communities and their entities from Neo4j"""
    
    print("🔄 Extracting communities from Neo4j...")
    
    communities = {}
    
    with driver.session() as session:
        # Get all communities with their entities
        result = session.run("""
            MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
            RETURN c.id as community_id, 
                   c.specialty as specialty,
                   c.theme as theme,
                   c.size as size,
                   collect({
                       name: e.name,
                       type: e.type,
                       description: e.description
                   }) as entities
            ORDER BY c.size DESC
        """)
        
        for record in result:
            community_id = record['community_id']
            communities[community_id] = {
                'id': community_id,
                'specialty': record['specialty'],
                'theme': record['theme'],
                'size': record['size'],
                'entities': record['entities']
            }
    
    print(f"✅ Extracted {len(communities)} communities")
    return communities

def summarize_community_with_claude(bedrock_client, community_data):
    """Generate community summary using Claude Sonnet"""
    
    # Prepare entity information
    entity_info = []
    for entity in community_data['entities']:
        entity_str = f"- {entity['name']} ({entity['type']}): {entity.get('description', 'No description')}"
        entity_info.append(entity_str)
    
    entities_text = "\n".join(entity_info[:20])  # Limit to first 20 entities
    if len(community_data['entities']) > 20:
        entities_text += f"\n... and {len(community_data['entities']) - 20} more entities"
    
    # Create prompt for Claude
    prompt = f"""You are a medical expert analyzing a community of related medical entities. Please provide a comprehensive summary of this medical community.

Community Information:
- ID: {community_data['id']}
- Medical Specialty: {community_data['specialty']}
- Theme: {community_data['theme']}
- Size: {community_data['size']} entities

Entities in this community:
{entities_text}

Please provide:
1. A concise title for this community (max 10 words)
2. A detailed summary (2-3 paragraphs) explaining:
   - What this community represents in medical terms
   - Key medical concepts and relationships
   - Clinical significance and relevance
   - How these entities work together in medical practice

Format your response as JSON:
{{
    "title": "Community title here",
    "summary": "Detailed summary here"
}}"""

    try:
        # Call Claude Sonnet via Bedrock
        llm = bedrock_client
        response = llm.invoke(prompt)
        # Parse response - response is an AIMessage object
        claude_response = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from Claude's response
        try:
            # Find JSON in the response
            start_idx = claude_response.find('{')
            end_idx = claude_response.rfind('}') + 1
            json_str = claude_response[start_idx:end_idx]
            summary_data = json.loads(json_str)
            
            return {
                'title': summary_data.get('title', f"Medical Community {community_data['id']}"),
                'summary': summary_data.get('summary', 'Summary not available'),
                'success': True
            }
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                'title': f"Medical Community {community_data['id']} - {community_data['specialty']}",
                'summary': claude_response,
                'success': True
            }
            
    except Exception as e:
        print(f"❌ Error calling Claude for community {community_data['id']}: {e}")
        return {
            'title': f"Medical Community {community_data['id']} - {community_data['specialty']}",
            'summary': f"This community contains {community_data['size']} medical entities related to {community_data['specialty']}. Theme: {community_data['theme']}",
            'success': False
        }

def save_summaries_to_neo4j(driver, summaries):
    """Save community summaries back to Neo4j"""
    
    print("💾 Saving summaries to Neo4j...")
    
    with driver.session() as session:
        for community_id, summary_data in summaries.items():
            session.run("""
                MATCH (c:Community {id: $community_id})
                SET c.title = $title,
                    c.summary = $summary,
                    c.summarized = true
            """,
            community_id=community_id,
            title=summary_data['title'],
            summary=summary_data['summary'])
    
    print(f"✅ Saved {len(summaries)} summaries to Neo4j")

def save_summaries_to_files(summaries):
    """Save summaries to JSON files"""
    
    print("💾 Saving summaries to files...")
    
    # Ensure data/graphs directory exists
    import os
    os.makedirs('data/graphs', exist_ok=True)
    
    # Save detailed summaries
    with open('data/graphs/community_summaries_detailed.json', 'w') as f:
        json.dump(summaries, f, indent=2)
    
    # Save summary overview
    overview = {}
    for community_id, summary_data in summaries.items():
        overview[community_id] = {
            'title': summary_data['title'],
            'summary_preview': summary_data['summary'][:200] + "..." if len(summary_data['summary']) > 200 else summary_data['summary'],
            'success': summary_data['success']
        }
    
    with open('data/graphs/community_summaries_overview.json', 'w') as f:
        json.dump(overview, f, indent=2)
    
    print("✅ Summary files saved:")
    print("   - data/graphs/community_summaries_detailed.json")
    print("   - data/graphs/community_summaries_overview.json")

def generate_summary_queries():
    """Generate Neo4j queries to view summaries"""
    
    queries = {
        "1. All Community Summaries": """
MATCH (c:Community)
WHERE c.summarized = true
RETURN c.id as CommunityID, 
       c.title as Title,
       c.specialty as Specialty,
       c.size as Size,
       c.summary as Summary
ORDER BY c.size DESC
        """,
        
        "2. Communities with Summaries (Visual)": """
MATCH (c:Community)<-[:BELONGS_TO]-(e:Entity)
WHERE c.summarized = true
RETURN c, e
        """,
        
        "3. Large Community Summaries": """
MATCH (c:Community)
WHERE c.summarized = true AND c.size >= 20
RETURN c.title as Title, c.summary as Summary, c.size as Size
ORDER BY c.size DESC
        """,
        
        "4. Gastroenterology Community Summary": """
MATCH (c:Community)
WHERE c.specialty = 'Gastroenterology' AND c.summarized = true
RETURN c.title as Title, c.summary as Summary
        """,
        
        "5. All Specialties Summary Overview": """
MATCH (c:Community)
WHERE c.summarized = true
RETURN c.specialty as Specialty,
       count(c) as Communities,
       collect(c.title)[0..3] as SampleTitles
ORDER BY Communities DESC
        """
    }
    
    print(f"\n🎨 COMMUNITY SUMMARY VISUALIZATION QUERIES")
    print("="*60)
    print("Copy these into Neo4j Browser (http://localhost:7474):")
    
    for name, query in queries.items():
        print(f"\n{name}:")
        print("```cypher")
        print(query.strip())
        print("```")

def main():
    """Main function for community summarization"""
    
    print("🏥 COMMUNITY SUMMARIZATION WITH AWS BEDROCK CLAUDE")
    print("="*60)
    print("🤖 Using Claude Sonnet for medical community analysis!")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        return
    
    # Setup Bedrock client
    bedrock_client = setup_bedrock()
    if not bedrock_client:
        driver.close()
        return
    
    try:
        # Get communities from Neo4j
        communities = get_communities_from_neo4j(driver)
        
        if not communities:
            print("❌ No communities found in Neo4j. Run semantic_community_neo4j.py first!")
            return
        
        # Summarize each community with Claude
        summaries = {}
        total_communities = len(communities)
        
        print(f"\n🤖 Generating summaries for {total_communities} communities...")
        
        for i, (community_id, community_data) in enumerate(communities.items(), 1):
            print(f"\n📝 Summarizing Community {community_id} ({i}/{total_communities})...")
            print(f"   - Specialty: {community_data['specialty']}")
            print(f"   - Size: {community_data['size']} entities")
            
            summary_result = summarize_community_with_claude(bedrock_client, community_data)
            summaries[community_id] = summary_result
            
            print(f"   ✅ Title: {summary_result['title']}")
            
            # Show progress for large communities
            if i % 5 == 0:
                print(f"\n📊 Progress: {i}/{total_communities} communities summarized")
        
        # Save summaries to Neo4j
        save_summaries_to_neo4j(driver, summaries)
        
        # Save summaries to files
        save_summaries_to_files(summaries)
        
        # Generate visualization queries
        generate_summary_queries()
        
        # Display results
        print(f"\n📊 SUMMARIZATION RESULTS:")
        print(f"   - Total communities: {total_communities}")
        successful_summaries = sum(1 for s in summaries.values() if s['success'])
        print(f"   - Successfully summarized: {successful_summaries}")
        print(f"   - Failed summaries: {total_communities - successful_summaries}")
        
        print(f"\n🏷️  SAMPLE COMMUNITY TITLES:")
        sorted_communities = sorted(communities.items(), key=lambda x: x[1]['size'], reverse=True)
        for i, (community_id, _) in enumerate(sorted_communities[:5]):
            summary = summaries[community_id]
            print(f"   {i+1}. {summary['title']}")
        
        print(f"\n🎉 SUCCESS!")
        print(f"="*40)
        print(f"✅ Generated {successful_summaries} community summaries using Claude Sonnet")
        print(f"🌐 Open Neo4j Browser: http://localhost:7474")
        print(f"📊 Use the summary queries above to view results")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.close()
        print("\n🔌 Neo4j connection closed")

if __name__ == "__main__":
    main()
