"""Agentic AI: Plan -> Act (tool use) -> Observe -> Reflect loop using Claude."""
import os
import sys
import anthropic
from tools import TOOL_SCHEMAS, run_tool

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 8

SYSTEM = """You are an autonomous research & task agent.
For every goal:
1. PLAN: write a short numbered plan before acting.
2. ACT: call tools one or more at a time to carry out the plan.
3. OBSERVE: read tool results; if one fails or is insufficient, adjust the plan.
4. FINISH: when the goal is achieved, give a clear final answer.
Use recall_notes at the start to check for prior context, and save_note for
facts worth remembering. Never invent facts - use tools to verify."""

class Agent:
    def __init__(self):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.history = []

    def run(self, goal: str, verbose: bool = True) -> str:
        self.history.append({"role": "user", "content": goal})
        for step in range(1, MAX_STEPS + 1):
            resp = self.client.messages.create(
                model=MODEL, max_tokens=1500, system=SYSTEM,
                tools=TOOL_SCHEMAS, messages=self.history)
            self.history.append({"role": "assistant", "content": resp.content})

            for block in resp.content:
                if block.type == "text" and verbose and block.text.strip():
                    print(f"\n[Step {step}] THINK: {block.text.strip()}")

            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")

            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = run_tool(block.name, block.input)
                    if verbose:
                        print(f"[Step {step}] ACT: {block.name}({block.input}) -> {out[:200]}")
                    results.append({"type": "tool_result",
                                    "tool_use_id": block.id, "content": out})
            self.history.append({"role": "user", "content": results})
        return "Stopped: reached the maximum number of steps."

if __name__ == "__main__":
    agent = Agent()
    if len(sys.argv) > 1:
        print("\nFINAL ANSWER:", agent.run(" ".join(sys.argv[1:])))
    else:
        print("Agent ready. Type a goal (or 'quit').")
        while (goal := input("\nGoal> ").strip()) not in ("quit", "exit"):
            print("\nFINAL ANSWER:", agent.run(goal))
