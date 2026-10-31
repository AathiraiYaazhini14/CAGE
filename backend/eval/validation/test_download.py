import urllib.request
import json
import ssl
from pathlib import Path

# Create an unverified ssl context in case Windows certificate store needs it
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

candidates = [
    {
        "name": "xstest",
        "url": "https://raw.githubusercontent.com/paul-rottger/xstest-benchmark/main/xstest_v2_prompts.csv",
        "license": "CC-BY 4.0"
    },
    {
        "name": "jailbreak_llms",
        "url": "https://raw.githubusercontent.com/verazuo/jailbreak_llms/main/data/jailbreak_prompts.csv",
        "license": "MIT"
    },
    {
        "name": "rubend18_jailbreaks",
        "url": "https://raw.githubusercontent.com/rubend18/ChatGPT-Jailbreak-Prompts/main/prompts.csv",
        "license": "MIT"
    },
    {
        "name": "hackaprompt",
        "url": "https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset/raw/main/hackaprompt.jsonl",
        "license": "Apache-2.0"
    }
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

results = []
for c in candidates:
    print(f"Testing download: {c['name']} from {c['url']}...")
    try:
        req = urllib.request.Request(c["url"], headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            code = resp.getcode()
            sample_bytes = resp.read(2048)
            print(f"  [SUCCESS] HTTP {code}, read {len(sample_bytes)} bytes")
            results.append({
                "name": c["name"],
                "url": c["url"],
                "license": c["license"],
                "status": "success",
                "sample": sample_bytes[:200].decode("utf-8", errors="replace")
            })
    except Exception as e:
        print(f"  [FAILED] Error: {e}")
        results.append({
            "name": c["name"],
            "url": c["url"],
            "license": c["license"],
            "status": "failed",
            "error": str(e)
        })

print("\nSummary of external dataset downloads:")
for r in results:
    print(f"  {r['name']:20s}: {r['status']} ({r['license']})")
