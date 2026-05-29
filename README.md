# Cafe Assistant (PoC)

A proof-of-concept conversational AI assistant for a casual cafe's online ordering app. Customers ask natural-language questions about the menu, dietary restrictions, and prices; the assistant answers using a strict prompt that prevents the LLM from inventing items, guessing prices, or claiming we sell things we don't.

Backed by Anthropic Claude (`claude-haiku-4-5`). Retrieval is lightweight keyword + dietary-tag matching over a mock 15-item menu.

---

## Files

| File | Purpose |
|---|---|
| `menu_data.py` | `MENU_DATA` — 15 mock cafe items with name, price, category, dietary tags, and keywords. |
| `assistant.py` | `answer_customer_query(user_question)` — retrieval + strict-prompt Claude call. |
| `cli.py` | Interactive REPL (`python cli.py`). |
| `golden_tests.py` | Automated 10-case validation suite (`python golden_tests.py`). |
| `requirements.txt` | Single dependency: `anthropic`. |

---

## Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file at the project root with your Anthropic key:
#    ANTHROPIC_API_KEY=sk-ant-...
# (See .env.example for the format. .env is gitignored.)
```

Alternatively, set the env var directly: `$env:ANTHROPIC_API_KEY = "sk-ant-..."` (PowerShell) or `export ANTHROPIC_API_KEY="sk-ant-..."` (Bash). The app uses `python-dotenv` to load `.env` automatically when the modules import.

---

## Run the assistant (REPL)

```powershell
python cli.py
```

Type questions at the `You:` prompt. Type `exit` or `quit` (or `Ctrl+C`) to leave.

### Suggested manual demo queries

Each query stresses a specific guardrail or retrieval behavior:

1. `do you have a caesar salad?` — direct lookup; should confirm the item and state the exact price.
2. `what's vegan?` — should list **every** item tagged `vegan`.
3. `how much is the classic latte?` — should state the exact menu price, no rounding.
4. `do you sell sushi?` — should apologize ("we don't currently offer that on our menu"). Must not invent a sushi-like dish.
5. `is the burger $50?` — **critical guardrail test.** Must not confirm "$50" and must not volunteer a fake burger price. Should apologize.
6. `something cold and sweet` — should surface drinks/desserts via inexact keyword retrieval.
7. `a gluten-free lunch under $15` — should list only gluten-free salads/sandwiches/pastas priced ≤ $15.

---

## Run the golden validation set

Automated regression suite. Use after any change to the system prompt, retrieval logic, or `MENU_DATA`.

```powershell
python golden_tests.py
```

- 10 fixed queries, one Claude call each (~pennies on Haiku).
- Substring-based assertions: `must_contain_any`, `must_contain_all`, `must_not_contain`, `must_contain_n_of`.
- Exit code 0 on full pass, 1 on any failure (CI-friendly).
- On failure: prints the query, the truncated response, and which assertion failed.

The most important case is **G05** (`is the burger $50?`) — a pass proves the anti-validation clause holds.

---

## The three guardrails

The system prompt strictly instructs Claude to:

1. **Never invent menu items** — only discuss items present in the retrieved MENU section.
2. **Never guess prices** — only state prices that appear verbatim in MENU.
3. **Apologize for missing items** — respond with an apology if a requested item is not on the menu.

Plus an anti-validation clause: if the customer asserts a price ("is the burger $50?"), do not agree, disagree, or repeat that price unless it matches the menu.
