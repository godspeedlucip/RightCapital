from pathlib import Path

root = Path(__file__).resolve().parents[2]
readme = (root / "README.md").read_text(encoding="utf-8")
ai = (root / "AI使用说明.md").read_text(encoding="utf-8")
required = ["Python", "MVP", "docker compose", "python -m pytest -q", "POST /v1/notifications"]
missing = [item for item in required if item not in readme]
required_ai = ["\u4e00\u3001AI \u63d0\u4f9b\u5e2e\u52a9\u7684\u5730\u65b9", "\u4e8c\u3001\u672a\u91c7\u7eb3\u7684\u5efa\u8bae", "\u4e09\u3001\u4f5c\u8005\u505a\u51fa\u7684\u5173\u952e\u51b3\u7b56"]
missing += [item for item in required_ai if item not in ai]
if missing:
    raise SystemExit("missing documentation: " + ", ".join(missing))
print("documentation checks passed")