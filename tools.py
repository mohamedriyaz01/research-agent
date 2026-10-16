"""Tools the agent can call. Each tool = JSON schema (for the LLM) + Python function."""
import ast
import json
import operator as op
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path("agent_memory.json")

# ---------- Safe calculator ----------
_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg, ast.FloorDiv: op.floordiv}

def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ValueError("Exponent too large")  # prevents CPU/memory exhaustion
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")

def calculator(expression: str) -> str:
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as e:
        return f"Error: {e}"

# ---------- Clock ----------
def current_time() -> str:
    return datetime.now().strftime("%A, %d %B %Y, %H:%M")

# ---------- Wikipedia search (no API key needed) ----------
def wikipedia_search(query: str) -> str:
    try:
        q = urllib.parse.quote(query)
        url = ("https://en.wikipedia.org/w/api.php?action=query&list=search"
               f"&srsearch={q}&srlimit=1&format=json")
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchAgent/1.0"})
        title = json.load(urllib.request.urlopen(req, timeout=10))["query"]["search"][0]["title"]
        s_url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                 + urllib.parse.quote(title))
        req = urllib.request.Request(s_url, headers={"User-Agent": "ResearchAgent/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=10))
        return f"{data['title']}: {data['extract']}"
    except Exception as e:
        return f"Search failed: {e}"

# ---------- Long-term memory ----------
def _load():
    return json.loads(MEMORY_FILE.read_text()) if MEMORY_FILE.exists() else {}

def save_note(key: str, value: str) -> str:
    mem = _load()
    mem[key] = value
    MEMORY_FILE.write_text(json.dumps(mem, indent=2))
    return f"Saved '{key}'."

def recall_notes(key: str = "") -> str:
    mem = _load()
    if key:
        return mem.get(key, f"No note named '{key}'.")
    return json.dumps(mem) if mem else "Memory is empty."

# ---------- Registry ----------
FUNCTIONS = {"calculator": calculator, "current_time": current_time,
             "wikipedia_search": wikipedia_search, "save_note": save_note,
             "recall_notes": recall_notes}

TOOL_SCHEMAS = [
    {"name": "calculator", "description": "Evaluate a math expression, e.g. '(12*7)/3'.",
     "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}},
                      "required": ["expression"]}},
    {"name": "current_time", "description": "Get the current date and time.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "wikipedia_search", "description": "Look up a factual summary on Wikipedia.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "save_note", "description": "Store a fact in long-term memory.",
     "input_schema": {"type": "object", "properties": {"key": {"type": "string"},
                      "value": {"type": "string"}}, "required": ["key", "value"]}},
    {"name": "recall_notes", "description": "Read long-term memory (one key, or all if empty).",
     "input_schema": {"type": "object", "properties": {"key": {"type": "string"}}}},
]

def run_tool(name: str, args: dict) -> str:
    fn = FUNCTIONS.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return fn(**args)
    except TypeError as e:
        return f"Bad arguments: {e}"
