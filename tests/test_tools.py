import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import tools

def test_calculator():
    assert tools.calculator("(12*7)/3") == "28.0"
    assert tools.calculator("__import__('os')").startswith("Error")

def test_calculator_blocks_huge_power():
    assert tools.calculator("9**9**9").startswith("Error")

def test_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "MEMORY_FILE", tmp_path / "m.json")
    tools.save_note("city", "Tiruppur")
    assert tools.recall_notes("city") == "Tiruppur"

def test_dispatch():
    assert tools.run_tool("nope", {}).startswith("Unknown")
    assert "Bad arguments" in tools.run_tool("calculator", {})
