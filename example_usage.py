"""
Example Usage
=============

Example script showing how to use the OpenAI-compatible API with the OpenAI Python client.
"""

import os
from openai import OpenAI

# Configuration
API_BASE_URL = "http://localhost:8000/v1"
API_KEY = "sk-demo1234567890abcdef1234567890abcdef1234567890abcdef"

def main():
    """Main example function."""
    print("OpenAI-Compatible API Usage Example")
    print("=" * 40)
    
    # Initialize the OpenAI client with our local server
    client = OpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL
    )
    
    try:
        # Example 1: List available models
        print("\n1. Listing available models:")
        models = client.models.list()
        for model in models.data:
            print(f"   - {model.id} (owned by {model.owned_by})")
        
        # Example 2: Simple chat completion
        print("\n2. Simple chat completion:")
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "user", "content": "Hello! Please introduce yourself briefly."}
            ],
            temperature=0.7
        )
        
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Usage: {response.usage.total_tokens} tokens")
        
        # Example 3: Multi-turn conversation
        print("\n3. Multi-turn conversation:")
        messages = [
            {"role": "system", "content": "You are a helpful assistant that loves to tell jokes."},
            {"role": "user", "content": "Tell me a programming joke."}
        ]
        
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=messages,
            temperature=0.8
        )
        
        print(f"   Assistant: {response.choices[0].message.content}")
        
        # Add the assistant's response to continue the conversation
        messages.append({
            "role": "assistant", 
            "content": response.choices[0].message.content
        })
        messages.append({
            "role": "user", 
            "content": "That's funny! Tell me another one about AI."
        })
        
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=messages,
            temperature=0.8
        )
        
        print(f"   Assistant: {response.choices[0].message.content}")
        
        # Example 4: Streaming response
        print("\n4. Streaming response:")
        print("   Assistant: ", end="", flush=True)
        
        stream = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "user", "content": "Count from 1 to 10, but make it interesting with emojis."}
            ],
            stream=True,
            temperature=0.7
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="", flush=True)
        
        print("\n")
        
        # Example 5: Different temperature settings
        print("\n5. Temperature comparison:")
        
        prompt = "Describe the color blue in one sentence."
        
        for temp in [0.1, 0.7, 1.5]:
            response = client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=50
            )
            
            print(f"   Temperature {temp}: {response.choices[0].message.content}")
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure the API server is running:")
        print("   python start_server.py")


if __name__ == "__main__":
    main()