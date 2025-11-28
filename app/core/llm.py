"""
LLM Client (Groq)
Centralized wrapper for Groq API interactions.
Ported from financial-guardian-backend/app/core/llm.py
"""

import os
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class LLMClient:
    """Wrapper for Groq API"""
    
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("⚠️  GROQ_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
        self.model = "openai/gpt-oss-20b"
        
    def is_available(self) -> bool:
        return self.client is not None

    def generate_response(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False,
        temperature: float = 0.1,
        model: Optional[str] = None
    ) -> str:
        """Generate a response from the LLM"""
        if not self.client:
            raise RuntimeError("Groq client not initialized. Check GROQ_API_KEY.")
            
        try:
            kwargs = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "model": model or self.model,
                "temperature": temperature,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
                
            completion = self.client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
            
        except Exception as e:
            print(f"❌ LLM Error: {str(e)}")
            raise e

    def generate_vision_response(
        self,
        prompt: str,
        base64_image: str,
        temperature: float = 0.1
    ) -> str:
        """
        Generate a response from the Vision LLM (OpenAI GPT-4o).
        Used for receipt scanning and image analysis.
        """
        from openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in environment variables.")
             
        try:
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=temperature,
                max_tokens=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Vision LLM Error: {str(e)}")
            raise e


# Global instance
llm_client = LLMClient()
