"""
AI & Multimodal Routes Blueprint
Handles Groq LLM chatbot interactions and Qwen Vision image analysis for pollution detection.
"""

from flask import Blueprint, jsonify, request
import os
import json
import base64
import time
from groq import Groq
from services.supabase_service import supabase_insert

ai_bp = Blueprint('ai', __name__)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = None

if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("[INFO] Groq client initialized successfully")
    except Exception as e:
        print(f"[ERROR] Groq client initialization failed: {e}")


@ai_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Conversational AI assistant powered by Groq Qwen 3.8 27B."""
    if not groq_client:
        return jsonify({'error': 'AI chat service unavailable – GROQ_API_KEY missing'}), 503

    data     = request.get_json(silent=True) or {}
    message  = data.get('message', '').strip()
    history  = data.get('history', [])
    language = data.get('language', 'English')

    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    system_prompt = f"""You are Ganga Sentinel AI, an intelligent, empathetic environmental assistant for the River Sentinel project.
You monitor the Ganga River in Varanasi, India.
Your mission is to help citizens and authorities protect the river, stay safe from floods, understand water quality parameters (pH, Turbidity, DO, BOD, COD), and report pollution.
Always respond in {language}.
Keep answers concise (under 120 words), accurate, culturally respectful of Varanasi, and actionable.
Format key advice with bullet points when helpful."""

    messages = [{'role': 'system', 'content': system_prompt}]
    for turn in history[-6:]:
        messages.append({'role': turn.get('role', 'user'), 'content': turn.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    try:
        completion = groq_client.chat.completions.create(
            messages=messages,
            model='qwen/qwen3.8-27b',
            temperature=0.6,
            max_tokens=800
        )
        reply = completion.choices[0].message.content.strip()
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"[ERROR] Groq chat completion error: {e}")
        return jsonify({'error': 'Failed to generate AI response. Please try again.'}), 500


@ai_bp.route('/api/ai/analyze-image', methods=['POST'])
def analyze_image():
    """Multimodal image pollution assessment using Groq Qwen Vision."""
    if not groq_client:
        return jsonify({'error': 'Groq client not configured'}), 503

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']
    if not image_file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    try:
        image_bytes   = image_file.read()
        b64_image     = base64.b64encode(image_bytes).decode('utf-8')
        mime_type     = image_file.mimetype or 'image/jpeg'

        prompt = (
            'Analyze this river image for pollution. Return ONLY raw JSON:\n'
            '{"pollution_level":"Low"|"Moderate"|"High"|"Critical",'
            '"confidence":<0-100>,'
            '"pollutants":["list"],'
            '"assessment":"brief description"}'
        )

        completion = groq_client.chat.completions.create(
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {
                        'url': f"data:{mime_type};base64,{b64_image}"
                    }}
                ]
            }],
            model='qwen/qwen3.8-27b',
            temperature=0.1,
            max_tokens=512
        )

        raw = completion.choices[0].message.content.strip()
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0].strip()
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0].strip()

        result = json.loads(raw)

        # Persist report directly into Supabase
        try:
            supabase_insert('pollution_reports', {
                'pollution_level': result.get('pollution_level', 'Moderate'),
                'pollutants': result.get('pollutants', []),
                'assessment': result.get('assessment', ''),
                'description': f"AI-assisted image evaluation (confidence: {result.get('confidence', 75)}%)",
                'location_name': 'Ganga River',
                'reporter': 'Citizen AI',
                'status': 'PENDING'
            })
        except Exception as se:
            print(f"[WARNING] Supabase pollution report save failed: {se}")

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Image analysis error: {e}")
        return jsonify({'error': str(e)}), 500
