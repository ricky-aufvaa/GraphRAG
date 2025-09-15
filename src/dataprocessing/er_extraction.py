import json
import boto3
from langchain_aws import ChatBedrock
from dotenv import load_dotenv
import os
from src.config.prompts import medical_system_prompt
load_dotenv()

PROC_BASE_DIR = "data/processed/"
PROCESSED_CHUNKS = os.path.join(PROC_BASE_DIR,"processed_chunks.json")
PROC_BASE_DIR = "data/processed/"
ER_EXTRACTION = os.path.join(PROC_BASE_DIR,"er_extraction.json")

print(os.getenv("AWS_ACCESS_KEY_ID"))
#AWS bedrock setup
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

medical_prompt = medical_system_prompt

def extract_from_text(text,llm):
    """Extract entities and relationships from a single piece of text"""

    full_prompt = medical_prompt + "\n\nCLINICAL TEXT:\n" + text

    try:
        #call the LLM
        response = llm.invoke(full_prompt)
        raw_content = response.content if hasattr(response,'content') else str(response)
        #try t oparse the json
        try:
            result = json.loads(raw_content)
            print(f"Extracted {len(result.get('entities',[]))} entities, {len(result.get('relationships',[]))} relationships")
            return result
        except json.JSONDecodeError:
            print("json parsing failed")
            return {"entities": [],"relationships": []}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"entities": [],"relationships": []}

def process_all_chunks(chunks_file = PROCESSED_CHUNKS, output_file=ER_EXTRACTION,max_chunks=None):
    """
        Process all text chunks and extract entities and relationships
    """
    print("starting entity extraction")
    llm = setup_bedrock()
    with open(chunks_file,'r') as f:
        chunks = json.load(f)
    
    #limit chunks if specified
    if max_chunks:
        chunks = chunks[:max_chunks]
        print(f"Processing first {max_chunks} chunks for testing..")

    print(f"Processing {len(chunks)} chunks...")

    all_extractions = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}: {chunk['chunk_id']}")
        
        # Extract from this chunk
        extraction = extract_from_text(chunk['text'], llm)
        
        # Add chunk info
        extraction['chunk_id'] = chunk['chunk_id']
        extraction['source_file'] = chunk['source_file']
        extraction['chunk_index'] = chunk['chunk_index']
        
        all_extractions.append(extraction)
        
        # Small delay to avoid rate limits
        # time.sleep(0.5)
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(all_extractions, f, indent=2)
    
    print(f"💾 Saved {len(all_extractions)} extractions to {output_file}")
    return all_extractions


def analyze_extractions(extractions):
    """Analyze the extraction results"""
    
    total_entities = 0
    total_relationships = 0
    entity_types = {}
    relationship_types = {}
    errors = 0
    
    for extraction in extractions:
        if 'error' in extraction:
            errors += 1
            continue
        
        # Count entities
        entities = extraction.get('entities', [])
        total_entities += len(entities)
        
        for entity in entities:
            entity_type = entity.get('type', 'UNKNOWN')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Count relationships
        relationships = extraction.get('relationships', [])
        total_relationships += len(relationships)
        
        for rel in relationships:
            rel_type = rel.get('relationship', 'UNKNOWN')
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
    
    successful_chunks = len(extractions) - errors
    
    print("\n📊 EXTRACTION STATISTICS:")
    print(f"   - Total chunks: {len(extractions)}")
    print(f"   - Successful: {successful_chunks}")
    print(f"   - Failed: {errors}")
    print(f"   - Total entities: {total_entities}")
    print(f"   - Total relationships: {total_relationships}")
    print(f"   - Avg entities per chunk: {total_entities / successful_chunks if successful_chunks > 0 else 0:.1f}")
    print(f"   - Avg relationships per chunk: {total_relationships / successful_chunks if successful_chunks > 0 else 0:.1f}")
    
    print(f"\n🏷️ Entity Types:")
    for entity_type, count in entity_types.items():
        print(f"   - {entity_type}: {count}")
    
    print(f"\n🔗 Relationship Types:")
    for rel_type, count in relationship_types.items():
        print(f"   - {rel_type}: {count}")

# Main function to run everything
def main():
    """Main function - run this to extract entities"""
    
    print("🏥 SIMPLE MEDICAL ENTITY EXTRACTION")
    print("="*50)
    
    # Test with small batch first
    print("\n1️⃣ Testing with 3 chunks...")
    test_extractions = process_all_chunks(
        # chunks_file="processed_chunks.json",
        output_file="er_extractions_test.json", 
        max_chunks=3
    )
    
    if test_extractions:
        analyze_extractions(test_extractions)
        
        # Ask if user wants to run full extraction
        user_input = input("\n🤔 Run full extraction on all chunks? (y/n): ")
        if user_input.lower() == 'y':
            print("\n2️⃣ Running full extraction...")
            full_extractions = process_all_chunks(
                chunks_file="processed_chunks.json",
                output_file="simple_extractions_full.json"
            )
            analyze_extractions(full_extractions)

if __name__ == "__main__":
    main()
