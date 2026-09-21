import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv("../.env")
key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
req = urllib.request.Request(url)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        models = data.get("models", [])
        print(f"Total models returned: {len(models)}")
        content_models = []
        for m in models:
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                content_models.append(m.get("name"))
                print(f"Supported: {m.get('name')}")
        if not content_models:
            print("NO models support generateContent for this key!")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
