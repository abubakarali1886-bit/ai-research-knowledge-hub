"""
Summarize a document directly - Test script
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.services.summarization_service import SummarizationService

def summarize_document(document_id: int):
    db = SessionLocal()
    try:
        service = SummarizationService()
        result = service.summarize_document(document_id, db)
        
        if result.get('success', False):
            print("\n" + "="*60)
            print(f"📄 SUMMARY: {result.get('document_title', 'Unknown')}")
            print("="*60)
            
            summary = result.get('summary', {})
            
            if summary.get('research_objective'):
                print(f"\n🎯 RESEARCH OBJECTIVE:\n{summary['research_objective']}\n")
            
            if summary.get('methodology'):
                print(f"🔬 METHODOLOGY:\n{summary['methodology']}\n")
            
            if summary.get('key_findings'):
                print(f"📊 KEY FINDINGS:\n{summary['key_findings']}\n")
            
            if summary.get('main_conclusions'):
                print(f"✅ MAIN CONCLUSIONS:\n{summary['main_conclusions']}\n")
            
            if summary.get('policy_implications'):
                print(f"🏛️ POLICY IMPLICATIONS:\n{summary['policy_implications']}\n")
            
            print("="*60)
            print(f"Total chunks: {result.get('total_chunks', 0)}")
            print(f"Total characters: {result.get('total_characters', 0)}")
            print(f"Raw summary preview: {result.get('raw_summary', '')[:200]}...")
            print("="*60)
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Summarize document ID 1
    summarize_document(1)