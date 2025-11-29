"""
Translation Middleware for Multilingual Support
Supports 14+ Indian languages with auto-detection.
Uses Groq LLM for high-quality translations.
"""

import os
import re
from typing import Tuple, Optional
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# Make langdetect deterministic
DetectorFactory.seed = 0

# Supported Indian languages with their names
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu",
    "sa": "Sanskrit",
    # Additional languages that may be detected
    "ne": "Nepali",
    "si": "Sinhala",
}

# Language code to name mapping for translation prompts
LANG_NAMES = {
    "hi": "Hindi",
    "ta": "Tamil", 
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "si": "Sinhala",
}


def _create_translation_llm():
    """Create LLM for translation - uses fast model"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    return ChatGroq(
        model="openai/gpt-oss-20b",  # Good multilingual support
        temperature=0.1,  # Low temp for accurate translation
        groq_api_key=api_key,
        max_tokens=2048
    )


def _is_hinglish(text: str) -> bool:
    """
    Detect if text is Hinglish (Hindi written in Latin script).
    Uses heuristics based on common Hindi words in Latin script.
    """
    # Common Hindi words often written in Latin script
    hinglish_markers = [
        r'\b(kya|kaise|kab|kitna|kitne|kaun|kyun|kaha|kahan)\b',  # Question words
        r'\b(hai|hain|ho|tha|the|thi|hoga|hogi|kar|karo|karna|kare|karke)\b',  # Verbs
        r'\b(mera|meri|mere|tera|teri|tere|hamara|tumhara|apna|apni)\b',  # Pronouns
        r'\b(aur|ya|lekin|agar|toh|bhi|nahi|nhi|nahin|ke|ka|ki|ko|se|me|pe)\b',  # Conjunctions & postpositions
        r'\b(paisa|paise|rupay|rupees|rs)\b',  # Money
        r'\b(kitna|spend|kharcha|kharch|bach|bachat|goal|liye)\b',  # Financial
        r'\b(abhi|kal|aaj|parso|subah|sham|raat)\b',  # Time
        r'\b(accha|theek|sahi|galat|bahut|thoda|zyada)\b',  # Common adjectives
        r'\b(khareed|kharida|liya|diya|mila|bhej|bech|de|le|lo|do)\b',  # Verbs
        r'\b(bhai|yaar|dost|sir|ji|sahab)\b',  # Address terms
        r'\b(batao|bolo|dekho|suno|jao|aao|chalo)\b',  # Imperatives
        r'\b(wala|wali|wale|waala|waali|waale)\b',  # Suffixes
    ]
    
    text_lower = text.lower()
    matches = sum(1 for pattern in hinglish_markers if re.search(pattern, text_lower))
    
    # If 2+ Hindi markers found in Latin text, likely Hinglish
    return matches >= 2


def _has_devanagari(text: str) -> bool:
    """Check if text contains Devanagari script (Hindi/Marathi/Sanskrit)"""
    # Devanagari Unicode range: U+0900 to U+097F
    return bool(re.search(r'[\u0900-\u097F]', text))


def _has_non_latin_indian_script(text: str) -> bool:
    """Check if text contains any Indian language script"""
    indian_scripts = [
        r'[\u0900-\u097F]',  # Devanagari (Hindi, Marathi, Sanskrit)
        r'[\u0980-\u09FF]',  # Bengali/Assamese
        r'[\u0A00-\u0A7F]',  # Gurmukhi (Punjabi)
        r'[\u0A80-\u0AFF]',  # Gujarati
        r'[\u0B00-\u0B7F]',  # Odia
        r'[\u0B80-\u0BFF]',  # Tamil
        r'[\u0C00-\u0C7F]',  # Telugu
        r'[\u0C80-\u0CFF]',  # Kannada
        r'[\u0D00-\u0D7F]',  # Malayalam
        r'[\u0600-\u06FF]',  # Arabic (Urdu)
    ]
    return any(re.search(pattern, text) for pattern in indian_scripts)


def detect_language(text: str) -> str:
    """
    Detect the language of input text.
    
    Returns:
        Language code (e.g., 'en', 'hi', 'ta', 'hinglish')
    """
    if not text or len(text.strip()) < 3:
        return "en"
    
    # First check for Hinglish (Latin script with Hindi words)
    if not _has_non_latin_indian_script(text) and _is_hinglish(text):
        return "hinglish"
    
    # Try langdetect for script-based detection
    try:
        detected = detect(text)
        
        # Map to supported languages
        if detected in SUPPORTED_LANGUAGES:
            return detected
        
        # Fallback for unrecognized but Indian-script text
        if _has_non_latin_indian_script(text):
            if _has_devanagari(text):
                return "hi"  # Default Devanagari to Hindi
            return "hi"  # Default Indian scripts to Hindi for translation
        
        return "en"  # Default to English
        
    except LangDetectException:
        # If detection fails, check for Indian scripts
        if _has_non_latin_indian_script(text):
            return "hi"
        if _is_hinglish(text):
            return "hinglish"
        return "en"


async def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate text from source language to English.
    
    Args:
        text: Input text in source language
        source_lang: Detected source language code
        
    Returns:
        English translation
    """
    if source_lang == "en":
        return text
    
    llm = _create_translation_llm()
    
    # Get language name for prompt
    if source_lang == "hinglish":
        lang_name = "Hinglish (Hindi written in English/Latin script)"
    else:
        lang_name = LANG_NAMES.get(source_lang, "Indian language")
    
    prompt = f"""Translate the following {lang_name} text to English. 
This is a financial query, so preserve all numbers, amounts, and financial terms accurately.
Preserve the intent and meaning exactly.

Text to translate:
{text}

English translation (just the translation, no explanations):"""
    
    messages = [
        SystemMessage(content="You are a professional translator specializing in Indian languages. Translate accurately and naturally."),
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content.strip()


async def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translate text from English to target language.
    
    Args:
        text: English text to translate
        target_lang: Target language code
        
    Returns:
        Translated text in target language
    """
    if target_lang == "en":
        return text
    
    llm = _create_translation_llm()
    
    # Get language name for prompt
    if target_lang == "hinglish":
        lang_name = "Hinglish"
        script_instruction = "Use Latin/English script (Roman letters) with Hindi words and grammar. This is how young Indians text."
    else:
        lang_name = LANG_NAMES.get(target_lang, "Hindi")
        script_instruction = f"Use the native {lang_name} script."
    
    prompt = f"""Translate the following English text to {lang_name}.
{script_instruction}
This is a financial assistant response, so:
- Keep currency as ₹ or Rs.
- Keep numbers readable
- Be friendly and conversational
- Preserve any financial terms that are commonly used in English (like "budget", "goal", "SIP")

English text:
{text}

{lang_name} translation (just the translation, no explanations):"""
    
    messages = [
        SystemMessage(content=f"You are a professional translator. Translate to {lang_name} naturally and conversationally."),
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content.strip()


class TranslationMiddleware:
    """
    Middleware to handle multilingual input/output.
    Wraps around the main query processing.
    """
    
    def __init__(self):
        self.detected_language = "en"
    
    async def process_input(self, text: str) -> Tuple[str, str]:
        """
        Process input text - detect language and translate to English if needed.
        
        Returns:
            Tuple of (english_text, detected_language)
        """
        # Detect language
        self.detected_language = detect_language(text)
        print(f"🌐 Detected language: {self.detected_language}")
        
        # Translate if not English
        if self.detected_language != "en":
            english_text = await translate_to_english(text, self.detected_language)
            print(f"🔄 Translated to English: {english_text[:100]}...")
            return english_text, self.detected_language
        
        return text, "en"
    
    async def process_output(self, text: str, target_lang: Optional[str] = None) -> str:
        """
        Process output text - translate from English to target language if needed.
        
        Args:
            text: English response text
            target_lang: Optional target language (uses detected language if not specified)
            
        Returns:
            Translated response
        """
        lang = target_lang or self.detected_language
        
        if lang == "en":
            return text
        
        translated = await translate_from_english(text, lang)
        print(f"🔄 Translated response to {lang}")
        return translated


# Global middleware instance
_translation_middleware = None


def get_translation_middleware() -> TranslationMiddleware:
    """Get or create the translation middleware"""
    global _translation_middleware
    if _translation_middleware is None:
        _translation_middleware = TranslationMiddleware()
    return _translation_middleware


async def process_multilingual_query(user_id: int, query: str, process_fn) -> dict:
    """
    Wrapper function to add multilingual support to any query processor.
    
    Args:
        user_id: User ID
        query: Original query in any language
        process_fn: Async function that processes English query (e.g., process_query)
        
    Returns:
        Response dict with translated response
    """
    middleware = TranslationMiddleware()
    
    # Step 1: Detect and translate input to English
    english_query, detected_lang = await middleware.process_input(query)
    
    # Step 2: Process the English query
    result = await process_fn(user_id, english_query)
    
    # Step 3: Translate response back to detected language
    if detected_lang != "en" and "response" in result:
        result["response"] = await middleware.process_output(result["response"], detected_lang)
        result["detected_language"] = detected_lang
        result["original_query"] = query
        result["english_query"] = english_query
    else:
        result["detected_language"] = "en"
    
    return result
