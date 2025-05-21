import requests
import os
from dotenv import load_dotenv
load_dotenv() 
def analyze_audio_with_deepgram(audio_url):
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {
        "punctuate": "true",
        "language": "en",
        "model": "nova-3",
        "summarize": "v2",
        "topics": "true",
        "sentiment": "true",
        "intents": "true",
        "entities": "true",
        "detect_entities": "true",
        "smart_format": "true"
    }

    payload = {
        "url": audio_url
    }

    print(f"🔍 Sending this AUDIO_URL to Deepgram: {audio_url}")
    print("📦 Payload:", payload)

    response = requests.post("https://api.deepgram.com/v1/listen", headers=headers, params=params, json=payload)

    if response.ok:
        response_json = response.json()
        results = {
            "transcription": response_json.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        }

            # "summary": response_json.get("results", {}).get("summary", {}).get("short", ""),
            # "topics": response_json.get("results", {}).get("topics", {}).get("segments", []),
            # "sentiment": response_json.get("results", {}).get("sentiments", {}).get("average", {}),
            # "intents": response_json.get("results", {}).get("intents", []),
            # "entities": response_json.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("entities", [])
        
        print("REsults",results)
        return results
    else:
        raise Exception(f"Deepgram API error: {response.text}")
