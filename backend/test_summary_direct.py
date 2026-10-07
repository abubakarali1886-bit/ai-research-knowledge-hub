"""
Test summarization directly with Ollama
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test text
test_text = """
Monetary policy is the process by which a central bank controls the supply of money and credit.
The Bank of Tanzania implements monetary policy through various tools including reserve requirements,
open market operations, and the discount rate. The main objectives are price stability and economic growth.
In 2019, the central bank achieved its targets with reserve money growth of 11.5 percent.
The Monetary Policy Committee meets regularly to assess economic conditions and adjust policy accordingly.
"""

# Test Ollama directly
host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
model = os.getenv("LLM_MODEL", "deepseek-r1:1.5b")

print(f"=== Testing Ollama Summarization ===")
print(f"Model: {model}")
print(f"Host: {host}")
print("-" * 50)

prompt = f"""Summarize the following text in a clear and concise manner. Focus on the main points.

Text: {test_text}

Summary:"""

payload = {
    "model": model,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.3,
        "num_predict": 300
    }
}

try:
    print("Sending request to Ollama...")
    response = requests.post(
        f"{host}/api/generate",
        json=payload,
        timeout=60
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        summary = result.get('response', '').strip()
        print(f"\nSUMMARY:\n{summary}")
        print(f"\nLength: {len(summary)} characters")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")