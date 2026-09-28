"""
Vision Feature Extraction & Image Analysis
-------------------------------------------
Provides automated visual analysis for models or providers that do not
natively support multimodal image input. When a user sends an image while
a text-only model is active, this module extracts visual features and
summarizes the image content to be injected into the prompt context.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

VISION_PROMPT = (
    "Provide a comprehensive, highly detailed, and objective visual description of this image. "
    "Do not assume any persona or fictional context; describe purely what is visually observable. "
    "Detail every aspect thoroughly:\n"
    "1. Primary and secondary subjects: people, characters, animals, or central objects (their exact physical appearance, poses, facial expressions, actions, hairstyles, clothing, colors, and textures).\n"
    "2. Setting and environment: indoor/outdoor context, background objects, furniture, architecture, landscape, weather, lighting, spatial layout, and color palette.\n"
    "3. Visible text, typography, and graphics: transcribe all visible text verbatim, signs, logos, watermarks, UI elements, or diagrams.\n"
    "4. Overall composition and style: photography, digital art, illustration, screenshot, realistic or stylized, camera perspective, and notable fine details.\n"
    "Be as detailed, accurate, and descriptive as possible."
)


def analyze_image(image_data_uri: str) -> str:
    """
    Extracts a detailed visual description from an image Data URI using
    either Mistral Pixtral or OpenRouter Free Vision models.
    """
    if not image_data_uri or not isinstance(image_data_uri, str):
        return ""

    # Priority 1: Mistral Pixtral if MISTRAL_API_KEY is available
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        try:
            from mistralai.client import Mistral
            from mistralai.client.models import UserMessage

            client = Mistral(api_key=mistral_key)
            msg = UserMessage(
                content=[
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ]
            )
            print("[Vision] Extracting image analysis via Mistral 'pixtral-12b-2409'...")
            resp = client.chat.complete(
                model="pixtral-12b-2409",
                messages=[msg],
                temperature=0.2,
                max_tokens=1000,
            )
            content = resp.choices[0].message.content or ""
            if content.strip():
                print(f"\n[Vision] Extracted Image Context (Mistral Pixtral):\n{'-'*60}\n{content.strip()}\n{'-'*60}\n")
                return content.strip()
        except Exception as err:
            print(f"[Vision] Mistral vision extraction error: {err}")

    # Priority 2: OpenAI GPT-4o Mini if OPENAI_API_KEY is available
    try:
        from . import openai_model
        if openai_model.has_api_key():
            client = openai_model.get_client()
            print("[Vision] Extracting image analysis via OpenAI 'gpt-4o-mini'...")
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_PROMPT},
                            {"type": "image_url", "image_url": {"url": image_data_uri}},
                        ],
                    }
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            content = resp.choices[0].message.content or ""
            if content.strip():
                print(f"\n[Vision] Extracted Image Context (OpenAI GPT-4o Mini):\n{'-'*60}\n{content.strip()}\n{'-'*60}\n")
                return content.strip()
    except Exception as err:
        print(f"[Vision] OpenAI vision extraction error: {err}")

    # Priority 3: OpenRouter Free Models Router if OPENROUTER_APIKEY is available
    openrouter_key = os.getenv("OPENROUTER_APIKEY") or os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from openai import OpenAI

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/Lakshyakumar266/",
                    "X-Title": "Akari Watanabe",
                },
                timeout=60.0,
            )
            print("[Vision] Extracting image analysis via OpenRouter 'openrouter/free'...")
            resp = client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_PROMPT},
                            {"type": "image_url", "image_url": {"url": image_data_uri}},
                        ],
                    }
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            choice = resp.choices[0]
            content = choice.message.content or ""
            # Fallback if reasoning model put text in reasoning
            if not content.strip() and hasattr(choice.message, "reasoning"):
                reasoning = getattr(choice.message, "reasoning", "")
                if reasoning:
                    content = reasoning[-800:]
            if content.strip():
                print(f"\n[Vision] Extracted Image Context (OpenRouter):\n{'-'*60}\n{content.strip()}\n{'-'*60}\n")
                return content.strip()
        except Exception as err:
            print(f"[Vision] OpenRouter vision extraction error: {err}")

    print("[Vision] Warning: No vision provider succeeded in analyzing image.")
    return "An image was attached by the user, but visual feature extraction was unavailable."
