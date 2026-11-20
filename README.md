# ClarityAnalyst

**A simplified AI tool for understanding restaurant sales inquiries.**

ClarityAnalyst lets a small restaurant owner ask questions about their sales data in plain English and get answers they can trust. Instead of letting a language model guess numbers, the system has the model write pandas code, runs that code on the data, and reports the verified result. Everything runs locally on open-weight models through [Ollama](https://ollama.com), so the data never leaves the owner's computer.

This repository is the Week 10 progress snapshot for CS6180 - Foundations of Generative AI. It is currently a work in progress.

## Current status

The current prototype is a **command-line evaluation harness**: a benchmark runner, code execution in a separate process, and automatic scoring against validated answers. It does not yet accept custom questions or uploaded CSV files.

| Component | Status |
|---|---|
| Data pipeline (4 tables to one flat CSV, with invariants checked) | Done |
| Validated pilot benchmark (7 questions, SQL + pandas cross-checked) | Done |
| Config A: direct answer, no code | Done |
| Config B: code execution, basic prompt | Done |
| Configs C-G: schema prompt, worked examples, error-retry loop, decline rule, full pipeline | Planned |
| Expanded benchmark (15-20 questions) | Planned |
| Commercial API reference run | Planned |
| Upload-and-ask interface with a configuration dropdown | Planned |

## What it evaluates

Each configuration is run on the same benchmark questions with the same models:

| Config | Description |
|---|---|
| A | The model answers directly from the prompt (column names + 5 sample rows). No code. |
| B | The model writes pandas code for the same prompt; the code is executed and its output is the answer. |
| C-G | Planned: add a schema-aware prompt, worked examples, an error-retry loop, and a decline rule for unanswerable questions, one at a time and then combined, to measure each technique's contribution. |

Models: `qwen2.5:7b` and `mistral:latest`, run through Ollama.

## Dataset

[Restaurant Sales Dataset by Hour and Menu Item](https://databasesample.com/datasets/restaurant-sales-dataset-by-hour-and-menu-item) (synthetic, CC0). It has four tables: 20 menu items, 8 servers, 450 orders, and 887 order lines, covering 8 weeks from 3 March 2025. The SQLite dump is in `data/restaurant.sql`.

`src/build_data.py` loads the tables into SQLite and flattens them into one order-line CSV (`data/sales_flat.csv`, one row per order line). It also checks the dataset's built-in invariants on every row: revenue = unit price x quantity, cost = unit cost x quantity, and margin = revenue - cost.

Please note that the flat table has one row per order line, not per order. An order can have 1 to 3 lines, so counting orders means counting distinct `order_id` values.

## Benchmark and ground truth

`benchmark/questions.json` holds the 7 pilot questions: 3 simple, 3 multi-step, and 1 unanswerable. Each answerable question's correct answer was computed twice, in SQL on the original four tables and in pandas on the flat CSV (`src/ground_truth.py`). All six matched. The unanswerable question (revenue lost to comps or discounts) has no answer because the dataset has no such data.

The pilot set is small, so results are indicative, not statistically conclusive. It will be expanded to 15-20 questions.

## Setup

You need:

1. **Python 3** with pandas: `pip install pandas`
2. **Ollama**, installed and running ([ollama.com](https://ollama.com))
3. The two models:

```
ollama pull qwen2.5:7b
ollama pull mistral:latest
```

The experiments here ran on a laptop with an Intel Core i7-1255U, 16 GB RAM, and CPU-only inference (about 4 tokens/s for these 7B models), so a full run takes a while. No GPU is required.

## Usage

Run all commands from the repository's top folder. On Windows use `py`; on macOS/Linux use `python3`.

**Rebuild the flat dataset (optional; `data/sales_flat.csv` is already included):**

```
py src/build_data.py
```

**Re-verify the benchmark answers (optional; run `build_data.py` first):**

```
py src/ground_truth.py
```

**Run the benchmark:**

```
py src/runner.py --model qwen2.5:7b --configs A B
py src/runner.py --model mistral:latest --configs A B
```

Run the models one at a time so they do not compete for memory. Results are appended to `results/results.jsonl` after every question, so an interrupted run resumes where it stopped. To start over, delete or move that file.

**Summarize results:**

```
py src/summarize.py
```

This prints accuracy, code-execution success, and average time per configuration and model, plus the unanswerable question's answers for review.

## Repository layout

```
benchmark/questions.json   Pilot questions with validated answers and scoring rules
data/restaurant.sql        Original 4-table SQLite dump
data/sales_flat.csv        Flattened order-line table used by the runner
src/build_data.py          Load SQL dump, check invariants, write the flat CSV
src/ground_truth.py        Compute each answer in SQL and pandas and compare
src/runner.py              Run configs A and B on a model and score the results
src/summarize.py           Summarize results/results.jsonl
results/results.jsonl      Raw logged runs (prompt response, code, output, score, time)
```

## Preliminary results (pilot, 6 answerable questions)

| | Qwen 2.5 7B | Mistral 7B |
|---|---|---|
| A: direct answer, correct (of 6) | 0 | 0 |
| B: code execution, correct (of 6) | 4 | 2 |
| B: code ran without error (of 7) | 7 | 5 |

In code mode (config B), neither model handled the unanswerable question: Qwen reported a figure computed from margin, and Mistral reported 0.0. Scoring is automatic (number and label matching) and was checked by hand for the unanswerable question and for every failure. Full analysis is in the progress report.

## Known limitations

- The sandbox is a separate Python process with a 60-second timeout. It is not a hardened isolation layer and does not block file or network access.
- Config A sees only 5 sample rows, because the full table does not fit in a small local model's context at usable speed.
- Output is capped at 400 tokens for code generation. A verbose reply can be cut off before its code block closes, which currently breaks code extraction (observed for Mistral on one question). This is a planned fix.
- Scoring is keyword-based and number-based and is not a substitute for reading the raw answers.

## Development note

Claude (Anthropic) was used to assist with the pilot prototype by planning the architecture, writing data-processing and runner code, suggesting terminal commands for testing, formatting README for readability, and helping set up the rough draft for this progress report. All experiments were run on my own hardware, a Dell Inspiron 15 (3520) laptop, and I have reviewed the results.

## Author

Zeynab Idris, CS6180, Fall 2026