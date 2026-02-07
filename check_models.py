
import requests
import json

api_key = "AIzaSyBFFdNvXdN5D92KHGIljf49fWmw_SKEfMU"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"Found {len(models)} models:")
        for m in models:
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                print(f" - {m['name']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
