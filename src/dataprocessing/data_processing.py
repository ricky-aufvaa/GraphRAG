from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import glob
import json

DATA_DIR = "mimic_ex_500/"
PROC_BASE_DIR = "data/processed/"
PROCESSED_CHUNKS = os.path.join(PROC_BASE_DIR,"processed_chunks.json")


#load the data
def load_and_chunk_medical_reports(data_dir=DATA_DIR):
    """
    Load all the medical reports
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=100,
        separators=[
            "\n\n",
            "\n",
            " ",
            ".",
            "",
        ]
    )
    chunks = []
    report_files = glob.glob(os.path.join(data_dir,"*.txt"))
    for report_file in report_files:
        with open(report_file,'r',encoding='utf-8') as f:
            text = f.read()
        #split the text into chunks
        file_chunks = text_splitter.split_text(text)

        #add metadata to each chunk
        for i,chunk in enumerate(file_chunks):
            chunk_data = {
                'text':chunk,
                'source_file':os.path.basename(report_file),
                'chunk_id':f"{os.path.basename(report_file)}_chunk_{i}",
                'chunk_index':i
            }
            chunks.append(chunk_data)
    return chunks

    #save the chunks 
def save_chunks(chunks,output_file="processed_chunks.json",processed_base_dir=PROC_BASE_DIR):
    """
    save the chunks to JSON for later processing"""
    saved_file_loc = os.path.join(processed_base_dir,output_file)
    with open(saved_file_loc,'w') as f:
        json.dump(chunks,f,indent=2)
    
    print(f"Saved {len(chunks)} chunks to {output_file}")




def main():
    """Main function to process medical reports into chunks"""
    print("🏥 MEDICAL DATA PROCESSING")
    print("="*50)
    
    # Load and chunk medical reports
    chunks = load_and_chunk_medical_reports()
    print(f"Total chunks created: {len(chunks)}")
    
    # Save the chunks
    save_chunks(chunks)
    
    print("✅ Data processing completed!")

if __name__ == "__main__":
    main()
