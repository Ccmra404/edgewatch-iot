# 扩展路线：鉴权、看板与告警

本文档对应「学习优先」计划的后续里程碑，可按顺序实现，每一步都能在 README 中增加一小节演示说明。

## 1. 鉴权与安全

### 1.1 API 访问控制（推荐给 HTTP 查询）

- **目标**：`/devices/...` 不对公网裸奔。
- **方案 A（简单）**：静态 `X-API-Key` 头，中间件校验，密钥来自环境变量。
- **方案 B（常见）**：用户登录发 JWT，设备归属与 `device_id` 绑定校验。
- **实施要点**：
  - FastAPI `Depends` 提取密钥或 JWT。
  - 测试用 `TestClient` 注入合法/非法头，覆盖 401/403。

### 1.2 MQTT 侧安全

- **目标**：禁止匿名随意发布到生产 Topic。
- **步骤**：
  - Mosquitto 配置用户名密码或 TLS（`listener 8883` + 证书）。
  - 后端 `paho` 使用相同凭据；设备固件同步配置。
- **学习点**：区分「传输加密」与「身份认证」。

### 1.3 设备身份

- **每设备密钥**：Provisioning 时写入 NVS/efuse 侧密钥（固件不落明文仓库）。
- **证书**：TLS 客户端证书（更重，适合进阶）。

## 2. 数据层：从 SQLite 到时序库

- **现状**：SQLite 适合单机演示与中小流量。
- **升级路径**：
  1. 保留 `StorageBackend` 抽象，新增 `PostgresStorage` 或 TimescaleDB hypertable。
  2. 写入路径仍由 MQTT worker 调用；查询 API 改为带时间范围 `from_ts` / `to_ts`。
- **面试话术**：「先用 SQLite 保证可复现，接口抽象好后换时序库只换实现。」

## 3. Web 看板

- **最小版本**：React/Vite + 轮询 `GET .../recent?limit=60`。
- **更好体验**：后端 SSE 或 WebSocket 推送最新点；前端 ECharts 折线。
- **契约**：在 OpenAPI（FastAPI 自动生成 `/docs`）里固定 `payload` 字段含义，前后端共用一个 JSON Schema 更佳。

## 4. 告警

- **规则引擎**：温度超过阈值连续 N 次再触发（防抖）。
- **通知**：邮件、企业微信、Slack Webhook；异步队列（Redis + worker）避免阻塞 MQTT 回调。
- **可观测性**：结构化日志 + 指标（请求延迟、MQTT 重连次数）。

## 5. 建议实现顺序（学习曲线）

1. `X-API-Key` + README 安全章节（半天级）。  
2. 历史查询 `GET /devices/{id}/history?from=&to=`（基于现有存储扩展）。  
3. 最小 React 看板 + 环境变量配置 API 基址。  
4. Mosquitto 密码 + TLS 文档与 compose  profile（`docker compose --profile secure`）。  
5. 告警与队列（可作为独立子项目写在作品集里）。

完成每一项时，建议同时增加 **pytest 用例** 与 **README 验收步骤**，保持项目始终「可讲、可跑、可测」。
