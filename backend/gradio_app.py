"""Gradio playground for the hybrid RAG + price guardrail (optional surface).

    pip install gradio
    ANTHROPIC_API_KEY=x SECRET_KEY=<32+ chars> python gradio_app.py

A lightweight, retrieval-only demo (no LLM key needed) that exposes the pieces a
reviewer wants to poke at directly:
  • Hybrid product search (lexical + vector → RRF)
  • Knowledge-base / buying-guide semantic search
  • The deterministic price guardrail (validate_response)

It reads the seeded dev DB. The production app is the React SPA served by FastAPI;
this is a focused ML demo surface (and ticks the Gradio box).
"""

from __future__ import annotations

import gradio as gr

from app.core.db import SessionLocal
from app.ai.hybrid import hybrid_search_products, hybrid_search_kb
from app.ai.guardrails import validate_response


def search_products(query: str):
    db = SessionLocal()
    try:
        items = hybrid_search_products(db, query, k=8)
        return [[i.get("sku"), i["name"], f"${i['price']:.2f}", i["category"]] for i in items]
    finally:
        db.close()


def search_kb(query: str):
    db = SessionLocal()
    try:
        hits = hybrid_search_kb(db, query)
        return "\n\n".join(f"### {h.doc_title} › {h.heading or '(overview)'}\n{h.content[:400]}"
                           for h in hits[:4]) or "_No matching documents._"
    finally:
        db.close()


def check_guardrail(answer: str, grounded_prices: str):
    # grounded_prices: comma-separated dollar amounts the retrieval "returned"
    items = []
    for tok in grounded_prices.replace("$", "").split(","):
        tok = tok.strip()
        if tok:
            try:
                items.append({"price": float(tok)})
            except ValueError:
                pass
    res = validate_response(answer, items, allow_multiples=True)
    return ("✅ PASS — every price is grounded." if res.ok
            else f"🛑 BLOCKED — {res.reason}")


with gr.Blocks(title="Smart Handy Man — RAG & Guardrail Playground") as demo:
    gr.Markdown("# 🤖 Smart Handy Man — Hybrid RAG & Guardrail playground")
    with gr.Tab("Product search (hybrid RAG)"):
        q = gr.Textbox(label="Query", placeholder="cordless drill / something to cut plywood")
        out = gr.Dataframe(headers=["SKU", "Name", "Price", "Category"], label="Top results")
        q.submit(search_products, q, out)
        gr.Button("Search").click(search_products, q, out)
    with gr.Tab("Knowledge base (semantic)"):
        kq = gr.Textbox(label="Question", placeholder="difference between an impact driver and a hammer drill")
        kout = gr.Markdown()
        kq.submit(search_kb, kq, kout)
        gr.Button("Ask").click(search_kb, kq, kout)
    with gr.Tab("Price guardrail"):
        a = gr.Textbox(label="Draft answer", value="The drill is $79.99 and two cost $159.98.")
        g = gr.Textbox(label="Grounded prices (comma-separated)", value="79.99")
        gout = gr.Markdown()
        gr.Button("Validate").click(check_guardrail, [a, g], gout)


if __name__ == "__main__":
    demo.launch()
