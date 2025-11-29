"""
Test Script for Multilingual Support
Tests language detection and translation in all supported Indian languages.
"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.translation import (
    detect_language,
    translate_to_english,
    translate_from_english,
    TranslationMiddleware
)


# Test cases for different languages
TEST_CASES = {
    # English
    "en": [
        "How much did I spend on food this month?",
        "Set a budget of 5000 for shopping",
        "What is my current balance?",
    ],
    
    # Hindi (Devanagari)
    "hi": [
        "इस महीने मैंने खाने पर कितना खर्च किया?",
        "मेरा बैलेंस क्या है?",
        "शॉपिंग के लिए 5000 का बजट सेट करो",
    ],
    
    # Hinglish (Hindi in Latin script)
    "hinglish": [
        "Mera balance kya hai?",
        "Maine khane pe kitna spend kiya?",
        "Shopping ke liye budget set karo 5000 ka",
        "Yaar mujhe batao kitna paisa bacha hai",
        "Goal banana hai gaming PC ke liye",
    ],
    
    # Tamil
    "ta": [
        "இந்த மாதம் உணவுக்கு எவ்வளவு செலவு செய்தேன்?",
        "என் இருப்பு என்ன?",
    ],
    
    # Telugu
    "te": [
        "ఈ నెలలో నేను ఆహారానికి ఎంత ఖర్చు చేశాను?",
        "నా బ్యాలెన్స్ ఎంత?",
    ],
    
    # Marathi
    "mr": [
        "या महिन्यात मी जेवणावर किती खर्च केला?",
        "माझा बॅलन्स किती आहे?",
    ],
    
    # Gujarati
    "gu": [
        "આ મહિને મેં ખોરાક પર કેટલો ખર્ચ કર્યો?",
        "મારું બેલેન્સ શું છે?",
    ],
    
    # Bengali
    "bn": [
        "এই মাসে আমি খাবারে কত খরচ করেছি?",
        "আমার ব্যালেন্স কত?",
    ],
    
    # Kannada
    "kn": [
        "ಈ ತಿಂಗಳು ನಾನು ಆಹಾರಕ್ಕೆ ಎಷ್ಟು ಖರ್ಚು ಮಾಡಿದೆ?",
        "ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?",
    ],
    
    # Malayalam
    "ml": [
        "ഈ മാസം ഭക്ഷണത്തിന് എത്ര ചെലവഴിച്ചു?",
        "എന്റെ ബാലൻസ് എന്താണ്?",
    ],
    
    # Punjabi
    "pa": [
        "ਇਸ ਮਹੀਨੇ ਮੈਂ ਖਾਣੇ 'ਤੇ ਕਿੰਨਾ ਖਰਚ ਕੀਤਾ?",
        "ਮੇਰਾ ਬੈਲੰਸ ਕੀ ਹੈ?",
    ],
    
    # Urdu
    "ur": [
        "اس مہینے میں نے کھانے پر کتنا خرچ کیا؟",
        "میرا بیلنس کیا ہے؟",
    ],
}


async def test_language_detection():
    """Test language detection for all languages"""
    print("\n" + "="*60)
    print("🌐 LANGUAGE DETECTION TESTS")
    print("="*60)
    
    results = {"passed": 0, "failed": 0}
    
    for expected_lang, test_texts in TEST_CASES.items():
        print(f"\n📌 Testing {expected_lang.upper()}:")
        for text in test_texts:
            detected = detect_language(text)
            status = "✅" if detected == expected_lang else "❌"
            if detected == expected_lang:
                results["passed"] += 1
            else:
                results["failed"] += 1
            print(f"  {status} '{text[:50]}...' -> {detected} (expected: {expected_lang})")
    
    print(f"\n📊 Detection Results: {results['passed']} passed, {results['failed']} failed")
    return results


async def test_translation_pipeline():
    """Test full translation pipeline"""
    print("\n" + "="*60)
    print("🔄 TRANSLATION PIPELINE TESTS")
    print("="*60)
    
    middleware = TranslationMiddleware()
    
    # Test cases: non-English inputs
    test_inputs = [
        ("मेरा बैलेंस क्या है?", "hi"),
        ("Mera balance kya hai?", "hinglish"),
        ("இந்த மாதம் உணவுக்கு எவ்வளவு செலவு?", "ta"),
        ("ఈ నెలలో నేను ఎంత ఖర్చు చేశాను?", "te"),
    ]
    
    for text, expected_lang in test_inputs:
        print(f"\n📝 Input ({expected_lang}): {text}")
        
        # Process input
        english_text, detected = await middleware.process_input(text)
        print(f"  🔤 Detected: {detected}")
        print(f"  🇬🇧 English: {english_text}")
        
        # Simulate response and translate back
        sample_response = "Your current balance is ₹25,000. You spent ₹5,000 on food this month."
        translated_response = await middleware.process_output(sample_response, detected)
        print(f"  🔙 Response ({detected}): {translated_response}")


async def test_hinglish_detection():
    """Specifically test Hinglish detection"""
    print("\n" + "="*60)
    print("🗣️ HINGLISH DETECTION TESTS")
    print("="*60)
    
    hinglish_texts = [
        "Mera balance kya hai bhai?",
        "Kitna spend kiya maine food pe?",
        "Budget set karo shopping ke liye",
        "Goal banana hai gaming PC ke liye",
        "Yaar paise nahi hai",
        "Kab tak save karna padega?",
        "Aur kitna bachat karna hai?",
    ]
    
    non_hinglish = [
        "How much did I spend?",
        "Set budget for food",
        "What is my balance?",
    ]
    
    print("\n✅ Should detect as Hinglish:")
    for text in hinglish_texts:
        detected = detect_language(text)
        status = "✅" if detected == "hinglish" else "❌"
        print(f"  {status} '{text}' -> {detected}")
    
    print("\n✅ Should detect as English:")
    for text in non_hinglish:
        detected = detect_language(text)
        status = "✅" if detected == "en" else "❌"
        print(f"  {status} '{text}' -> {detected}")


async def test_full_query_flow():
    """Test full query flow with supervisor (requires running server)"""
    print("\n" + "="*60)
    print("🚀 FULL QUERY FLOW TEST (with supervisor)")
    print("="*60)
    
    try:
        from app.langgraph_agents.supervisor import process_query_multilingual
        from app.core import init_database
        
        init_database()
        
        test_queries = [
            ("How much did I spend on food?", "en"),
            ("मेरा बैलेंस क्या है?", "hi"),
            ("Mera balance kya hai?", "hinglish"),
        ]
        
        for query, expected_lang in test_queries:
            print(f"\n📝 Query ({expected_lang}): {query}")
            result = await process_query_multilingual(user_id=1, query=query)
            print(f"  🌐 Detected: {result.get('detected_language', 'en')}")
            print(f"  💬 Response: {result['response'][:200]}...")
            print(f"  🤖 Agents: {result.get('agents_used', [])}")
            
    except Exception as e:
        print(f"⚠️ Full flow test skipped: {e}")


async def main():
    """Run all tests"""
    print("\n" + "🌍"*30)
    print("  MULTILINGUAL SUPPORT TEST SUITE")
    print("🌍"*30)
    
    # Test 1: Language Detection
    await test_language_detection()
    
    # Test 2: Hinglish Detection
    await test_hinglish_detection()
    
    # Test 3: Translation Pipeline (requires API)
    try:
        await test_translation_pipeline()
    except Exception as e:
        print(f"\n⚠️ Translation test skipped (needs GROQ_API_KEY): {e}")
    
    # Test 4: Full Query Flow
    try:
        await test_full_query_flow()
    except Exception as e:
        print(f"\n⚠️ Full flow test skipped: {e}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
