"""Run configs A (direct answer) and B (code execution, basic prompt) on the benchmark.
Usage: python src/runner.py --model qwen2.5:7b --configs A B
       python src/runner.py --model mock --configs A B     (self-test, no Ollama needed)
Results are appended to results/results.jsonl after every question, so interrupted runs resume."""
import argparse, json, os, re, subprocess, sys, tempfile, time, urllib.request
import pandas as pd

CSV = os.path.abspath("data/sales_flat.csv")
OUT = "results/results.jsonl"
df = pd.read_csv(CSV)
COLS = ", ".join(df.columns)
PREVIEW = df.head(5).to_string(index=False)

def prompt_A(q):
    return (f"You are a data analyst. A restaurant sales table has these columns: {COLS}.\n"
            f"Here are the first 5 rows:\n{PREVIEW}\n\n"
            f"Question: {q}\nAnswer the question directly and briefly.")

def prompt_B(q):
    return (f"A pandas DataFrame named df is already loaded with these columns: {COLS}.\n"
            f"Here are the first 5 rows:\n{PREVIEW}\n\n"
            f"Write Python code that answers this question and prints the answer: {q}\n"
            f"Return only code in one ```python block.")

def ollama(model, prompt, num_predict):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": 4096}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=600)); dt = time.time() - t
    return r["response"], dt, r.get("eval_count", 0)

def mock(model, prompt, num_predict):  # self-test only
    if "Write Python code" in prompt:
        return "Sure!\n```python\nprint(df.revenue.sum())\n```\nDone.", 0.0, 10
    return "The total is about $13,000.", 0.0, 10

def extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()

def run_code(code, timeout=60):
    """Run generated code in a separate process with a timeout (not a hardened sandbox)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "gen.py")
        open(path, "w", encoding="utf-8").write(
            f"import pandas as pd\ndf = pd.read_csv(r'{CSV}')\n{code}\n")
        try:
            p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout, cwd=d)
            return p.returncode == 0, p.stdout.strip(), p.stderr.strip()[-400:]
        except subprocess.TimeoutExpired:
            return False, "", "TIMEOUT"

DECLINE = re.compile(r"cannot|can't|can not|not (available|possible|contain|include|recorded|tracked)|no (data|information|record)|does not (contain|include|have)|doesn't (contain|include|have)|unable|n/a|not enough", re.I)
def numbers(text):
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*\.?\d*", text) if x.replace(",", "").replace(".", "").replace("-", "").isdigit()]

def score(q, text):
    if q["kind"] == "decline":
        return bool(DECLINE.search(text))
    num_ok = any(abs(abs(n) - q["answer"]) < 0.01 for n in numbers(text))
    if q["kind"] == "number":
        return num_ok
    return num_ok and bool(re.search(q["label_regex"], text, re.I))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--configs", nargs="+", default=["A", "B"])
    a = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT): r = json.loads(l); done.add((r["model"], r["config"], r["qid"]))
    gen = mock if a.model == "mock" else ollama
    for q in json.load(open("benchmark/questions.json")):
        for cfg in a.configs:
            if (a.model, cfg, q["id"]) in done: continue
            rec = dict(model=a.model, config=cfg, qid=q["id"], type=q["type"])
            if cfg == "A":
                text, dt, n = gen(a.model, prompt_A(q["question"]), 200)
                rec.update(raw=text, final=text, exec_ok=None)
            else:
                text, dt, n = gen(a.model, prompt_B(q["question"]), 400)
                code = extract_code(text); ok, out, err = run_code(code)
                rec.update(raw=text, code=code, exec_ok=ok, final=out if ok else f"ERROR: {err}", error=err)
            rec.update(correct=score(q, rec["final"]), seconds=round(dt, 1), tokens=n)
            open(OUT, "a").write(json.dumps(rec) + "\n")
            print(f"{a.model} {cfg} {q['id']} correct={rec['correct']} exec_ok={rec['exec_ok']} {dt:.0f}s", flush=True)

if __name__ == "__main__": main()
