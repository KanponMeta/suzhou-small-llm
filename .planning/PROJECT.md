# 企业知识库 RAG 系统

## What This Is

面向企业内部的文档知识库问答系统。支持上传 PDF、Word、Markdown 等中文文档，通过 RAG（检索增强生成）技术构建知识索引，对外提供 OpenAI 兼容的文本对话查询接口，并能从知识库内容自动生成符合平台规范的 `chat:text` 评测数据集，用于小语言模型的效果评测。

## Core Value

用户上传企业文档后，能通过标准 API 接口准确得到基于知识库内容的中文回答。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 支持上传 PDF、Word (.docx)、Markdown、纯文本文档
- [ ] 文档解析后自动切分、向量化，存入向量数据库
- [ ] 提供 OpenAI 兼容的 POST 查询接口（`model` + `messages` 格式）
- [ ] RAG 检索流程基于 LangGraph 编排：检索 → 增强 → 生成
- [ ] 调用阿里云百炼 DashScope API 完成 LLM 推理（qwen 系列模型）
- [ ] 从知识库文档自动生成 `evaluation_data.json` 格式的 `chat:text` 评测数据集
- [ ] 生成数据集支持导出为符合 `数据集提交指南.md` 规范的 `.zip` 压缩包
- [ ] 整个系统通过 Docker Compose 一键启动

### Out of Scope

- 多模态（图像/音频/视频）评测数据集生成 — MVP 仅关注 `chat:text` 类型
- Web 管理界面 — MVP 以 API 和 CLI 为交互方式，降低前端复杂度
- 多租户 / 权限管理 — 单租户企业内部部署，无需复杂权限体系
- 文档版本控制 / 知识图谱 — 超出 MVP 范围，可在后续迭代添加
- 流式响应（Streaming）— 接口规范仅要求标准 JSON 响应，不要求 SSE

## Context

- **接口规范**：查询接口须符合 `接口规范.md` 定义的 OpenAI 兼容格式，响应结构为 `choices[0].message.content`
- **数据集规范**：评测数据集须符合 `数据集提交指南.md` 中 `chat:text` 类型的格式要求（`evaluation_data.json` + `attachments/` 压缩为 `.zip`）
- **语言**：文档和问答以中文为主，embedding 和 LLM 均需支持中文
- **LLM 后端**：阿里云百炼 DashScope，使用 qwen 系列模型（如 `qwen-long` 用于生成，`text-embedding-v3` 用于向量化）
- **规范文件**：项目根目录下存有 `数据集提交指南.md` 和 `接口规范.md`，是本项目的外部约束文档

## Constraints

- **Tech Stack**: LangGraph 作为 LLM 编排框架 — 用户明确要求
- **LLM Provider**: 阿里云百炼 DashScope API — 统一使用，不引入 OpenAI 或其他境外服务
- **Deployment**: Docker Compose — 便于在企业内网环境快速部署
- **Language**: 中文优先 — embedding 模型和生成模型均须原生支持中文
- **API Compatibility**: 查询接口须 100% 符合 `接口规范.md` 定义的格式

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph 作为编排框架 | 用户明确指定，支持有状态的 RAG 流程图编排 | — Pending |
| 阿里云百炼 DashScope | 国内合规，中文模型质量高，统一 LLM 服务商 | — Pending |
| 向量数据库使用 ChromaDB | 轻量、无额外服务依赖、Docker 内嵌运行，适合 MVP | — Pending |
| 评测数据集自动生成 | 用 LLM 读取文档块，自动产生 Q&A 对，减少人工标注成本 | — Pending |
| MVP 无前端界面 | 降低复杂度，核心价值在于 API 和数据集生成能力 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after initialization*
