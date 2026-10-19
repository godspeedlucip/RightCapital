# API Notification Service

Python MVP for reliably delivering internal business notifications to external HTTP(S) supplier APIs.

## 问题理解

业务系统只负责提交通知任务，不需要直接处理供应商 API 的 URL、Header、Body、超时或重试。服务先持久化任务，再由 Worker 异步投递。

## 架构

```text
业务系统 -> FastAPI -> notifications 数据表 -> Worker -> 供应商 HTTP(S) API
```

服务采用至少一次投递语义：任务没有确认成功前可能重复发送。每次请求包含 `Idempotency-Key` 和 `X-Notification-ID`，供应商应使用它们完成去重。

## 系统边界与取舍

本 MVP 解决任务持久化、异步投递、超时、固定间隔重试、失败记录和租约恢复。不保证严格一次、不解析供应商业务响应、不实现 MQ、工作流编排、供应商管理后台或多区域容灾。

选择数据库任务表而不是消息队列，是因为作业规模下它依赖更少，并能直接验证状态、重试和恢复行为。流量显著增长后，可拆分 API/Worker、增加供应商级限流，再引入 MQ 和死信管理。

## 本地运行

要求 Python 3.12+。所有可运行实现位于 `MVP/` 文件夹。

```powershell
cd MVP
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m app.db
```

默认使用 SQLite；生产环境可将 `DATABASE_URL` 配置为 PostgreSQL 连接串。使用 Docker PostgreSQL：

```powershell
cd MVP
docker compose up -d db
```

启动 API 和 Worker：

```powershell
cd MVP
make run-api
make run-worker
```

## API 示例

创建接口：`POST /v1/notifications`

创建通知：

```powershell
cd MVP
curl.exe -X POST http://127.0.0.1:8000/v1/notifications `
  -H "Authorization: Bearer change-me" `
  -H "Content-Type: application/json" `
  -d '{"provider":"crm","event_type":"payment.succeeded","target":{"url":"https://vendor.example.com/hooks","method":"POST","headers":{},"body":{"payment_id":"p_123"}},"idempotency_key":"payment:p_123:crm"}'
```

成功返回 `202 Accepted`，只表示任务已持久化：

```json
{"notification_id":"ntf_...","status":"PENDING"}
```

查询状态：

```powershell
cd MVP
curl.exe http://127.0.0.1:8000/v1/notifications/ntf_... -H "Authorization: Bearer change-me"
```

## 测试

```powershell
cd MVP
python -m pytest -q
cd ..
python MVP/scripts/check-docs.py
python -m compileall MVP/app MVP/tests MVP/scripts
```

测试覆盖创建、幂等冲突、URL/Header 校验、成功投递、可重试/不可重试错误、固定退避、租约恢复和敏感信息脱敏。测试不依赖真实供应商账号。

## 关键配置

参见 [MVP/.env.example](MVP/.env.example)。默认最大尝试次数为 5 次，重试间隔为 10 秒，请求超时为 10 秒，租约为 30 秒。

## 作业提交

最终 GitHub 仓库名称应为 `rc_{your_nickname}`，并包含本 README、[MVP 实现](MVP/)、基于真实过程填写的 [AI 使用说明](AI使用说明.md)。
