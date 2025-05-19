import json
from pathlib import Path
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

# Geminiにプロンプトを送信する関数
def send_prompt(pdf_path, prompt, schema=None):
    client = genai.Client(api_key=GEMINI_API_KEY)
    use_model = "gemini-2.5-flash-preview-04-17"
    if pdf_path.exists():
        kwargs = dict(
            model=use_model,
            contents=[
                types.Part.from_bytes(
                    data=pdf_path.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
    else:
        kwargs = dict(
            model=use_model,
            contents=[prompt]
        )
    if schema:
        kwargs["config"] = {
            "response_mime_type": "application/json",
            "response_schema": schema,
        }
    response = client.models.generate_content(**kwargs)
    if schema and hasattr(response, "parsed"):
        return response.parsed
    return response.text