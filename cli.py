"""CLI REPL for the cafe assistant. Run with: python cli.py"""

from __future__ import annotations

import os
import sys

# Ensure UTF-8 output so the model's em-dashes and bullets render on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from assistant import answer_customer_query


BANNER = "Cafe assistant ready. Type 'exit' or 'quit' to leave."
PROMPT = "You: "
EXIT_WORDS = {"exit", "quit"}


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY environment variable is not set.\n"
            "Set it and try again. In PowerShell:\n"
            '  $env:ANTHROPIC_API_KEY = "sk-ant-..."',
            file=sys.stderr,
        )
        return 1

    print(BANNER)
    while True:
        try:
            user_input = input(PROMPT).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            print("Goodbye!")
            return 0

        if not user_input:
            print("Please type a question.")
            continue

        if user_input.lower() in EXIT_WORDS:
            print("Goodbye!")
            return 0

        answer = answer_customer_query(user_input)
        print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    sys.exit(main())
