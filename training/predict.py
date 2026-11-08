import argparse, json, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--out", required=True)
p.add_argument("--data", default="data/validation.jsonl")
p.add_argument("--max_new", type=int, default=64)
p.add_argument("--rp", type=float, default=1.0)
p.add_argument("--nr", type=int, default=0)
a = p.parse_args()
tok = AutoTokenizer.from_pretrained(a.model); tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(a.model).float().eval()
with open(a.out, "w") as f:
    for l in open(a.data):
        if not l.strip(): continue
        r = json.loads(l)
        x = tok(f"Command: {r['text']}\nJSON:", return_tensors="pt")
        with torch.no_grad():
            y = model.generate(**x, max_new_tokens=a.max_new, do_sample=False, repetition_penalty=a.rp, no_repeat_ngram_size=a.nr, pad_token_id=tok.pad_token_id)
        s = tok.decode(y[0][x["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        f.write(json.dumps({"id": r["id"], "prediction": s}) + "\n")
print("wrote", a.out)
