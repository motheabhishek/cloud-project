import json, os, requests

SHARD_INDEX = int(os.environ["SHARD_INDEX"])
SHARD_COUNT = int(os.environ["SHARD_COUNT"])
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
POOL = os.environ.get("POOL", "data/commands_pool.jsonl")
PROMPT_FILE = os.environ.get("PROMPT", "prompts/teacher_prompt.txt")
OUT_DIR = os.environ.get("OUT_DIR", "results/teacher")
LIMIT = int(os.environ.get("LIMIT", "0"))  # 0 = no limit; use a small number to test

template = open(PROMPT_FILE).read().rstrip("\n")
os.makedirs(OUT_DIR, exist_ok=True)
out_path = f"{OUT_DIR}/shard-{SHARD_INDEX}.jsonl"

done = set()
if os.path.exists(out_path):  # resume after a stop
    done = {json.loads(l)["id"] for l in open(out_path) if l.strip()}

lines = [l for l in open(POOL) if l.strip()]
mine = [json.loads(l) for i, l in enumerate(lines) if i % SHARD_COUNT == SHARD_INDEX]
if LIMIT:
    mine = mine[:LIMIT]

with open(out_path, "a") as out:
    for n, rec in enumerate(mine, 1):
        if rec["id"] in done:
            continue
        prompt = template.replace("{command}", rec["text"])
        r = requests.post(f"{OLLAMA}/api/generate", timeout=600, json={
            "model": "phi3.5", "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": 80,
                        "stop": ["\n\n", "Command:"]},
        })
        r.raise_for_status()
        out.write(json.dumps({"id": rec["id"], "text": rec["text"],
                              "teacher_raw": r.json()["response"]}) + "\n")
        out.flush()
        print(f"shard {SHARD_INDEX}: {n}/{len(mine)} {rec['id']}", flush=True)
