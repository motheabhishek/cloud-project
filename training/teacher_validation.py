import json, urllib.request
tmpl = open("prompts/teacher_prompt.txt").read()
out = open("results/pred_teacher.jsonl", "w")
for l in open("data/validation.jsonl"):
    if not l.strip(): continue
    r = json.loads(l)
    body = {"model": "phi3.5", "prompt": tmpl.replace("{command}", r["text"]),
            "stream": False, "options": {"temperature": 0, "seed": 42, "num_predict": 100}}
    req = urllib.request.Request("http://localhost:11434/api/generate",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=300).read())["response"]
    out.write(json.dumps({"id": r["id"], "prediction": resp}) + "\n"); out.flush()
    print(r["id"], flush=True)
out.close()
