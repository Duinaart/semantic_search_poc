#!/usr/bin/env python3
"""
Quick test script for Gemini 2.5 Flash Lite setup
"""

import os
from dotenv import load_dotenv
from llm_config import LLMConfig, create_llm
from query_transformer import QueryTransformer, Settings

def test_gemini_setup():
    """Test Gemini 2.5 Flash Lite configuration and connectivity."""
    
    print("🧪 Testing Gemini 2.5 Flash Lite Setup")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        print("\n📝 To fix this:")
        print("1. Get your API key from https://aistudio.google.com/")
        print("2. Add it to your .env file:")
        print("   GOOGLE_API_KEY=your_api_key_here")
        print("3. Set your provider:")
        print("   LLM_PROVIDER=google")
        print("   LLM_MODEL=gemini-2.5-flash-lite")
        return False
    
    print(f"✅ Google API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Check provider configuration
    providers = LLMConfig.get_available_providers()
    print(f"✅ Provider status: {providers['google']}")
    
    # Test LLM creation
    try:
        print("\n🔧 Creating Gemini 2.5 Flash Lite instance...")
        llm = create_llm(provider='google', model='gemini-2.5-flash-lite')
        print(f"✅ Successfully created: {llm.__class__.__name__}")
        print(f"✅ Model: {llm.model}")
        
        # Test actual API call
        print("\n🚀 Testing API call...")
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="Hello! Please respond with exactly: 'Gemini 2.5 Flash Lite is working!'")])
        print(f"✅ Response: {response.content}")
        
        # Test with QueryTransformer
        print("\n🔍 Testing QueryTransformer integration...")
        settings = Settings()
        print(f"✅ Current provider: {settings.LLM_PROVIDER}")
        print(f"✅ Current model: {settings.LLM_MODEL}")
        
        transformer = QueryTransformer(settings)
        result = transformer.transform("Find technology companies with high growth potential")
        
        if result and 'answer' in result:
            print("✅ QueryTransformer working successfully!")
            print(f"📝 Sample answer: {result['answer'][:100]}...")
        else:
            print("❌ QueryTransformer test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Gemini: {e}")
        return False
    
    print("\n🎉 All tests passed! Gemini 2.5 Flash Lite is ready to use.")
    print("\n💡 Benefits of Gemini 2.5 Flash Lite:")
    print("  • Ultra-fast response times")
    print("  • Cost-effective pricing") 
    print("  • Excellent performance on most tasks")
    print("  • Great results as mentioned in AI Studio")
    
    return True

if __name__ == "__main__":
    test_gemini_setup()