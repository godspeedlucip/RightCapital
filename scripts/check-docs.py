from pathlib import Path

readme=Path("README.md").read_text(encoding="utf-8")
ai=Path("docs/ai-usage.md").read_text(encoding="utf-8")
required=["架构","系统边界","至少一次","docker compose","make test","POST /v1/notifications"]
missing=[x for x in required if x not in readme]
required_ai=["AI 提供帮助的地方","未采纳的建议","自己做出的关键决策"]
missing += [x for x in required_ai if x not in ai]
if missing: raise SystemExit("missing documentation: " + ", ".join(missing))
print("documentation checks passed")
