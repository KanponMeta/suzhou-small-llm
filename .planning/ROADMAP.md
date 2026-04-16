# Roadmap: 企业知识库 RAG 系统

## Overview

从零构建一个企业内部文档知识库问答系统：先搭建可运行的基础设施并完成文档摄入流水线（Phase 1），再在此基础上构建基于 LangGraph 编排的 RAG 查询 API（Phase 2），最后实现从知识库内容自动生成评测数据集并导出为标准 ZIP 格式（Phase 3）。每个阶段都交付独立可验证的能力，且严格按照上游依赖顺序推进。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: 基础设施与文档摄入** - Docker 一键启动、DashScope 连通验证、文档解析/分块/向量化/持久化存储全链路
- [ ] **Phase 2: RAG 查询 API** - LangGraph 编排 RAG 流程，暴露符合接口规范的 OpenAI 兼容查询接口
- [ ] **Phase 3: 评测数据集生成** - 从知识库文档自动生成 chat:text Q&A 对，导出符合提交规范的 ZIP 压缩包

## Phase Details

### Phase 1: 基础设施与文档摄入
**Goal**: 系统可通过单条命令启动，DashScope 连通性已验证，用户可上传文档并查询已摄入的文件列表
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05
**Plans:** 2/3 plans executed
**Success Criteria** (what must be TRUE):
  1. `docker compose up` 成功启动所有服务，无需任何手动配置步骤
  2. `GET /health` 返回 HTTP 200，表示所有服务（包括 ChromaDB 和 DashScope 连通）均就绪
  3. 用户通过 `POST /documents/upload` 上传一份 PDF 文件后，文档内容被分块、向量化并持久存储，容器重启后数据不丢失
  4. 用户通过 `POST /documents/upload` 上传 Markdown 或纯文本文件后，内容同样被成功索引
  5. `GET /documents` 返回所有已摄入文档的列表（含 ID、文件名等元数据）

Plans:
- [x] 01-01-PLAN.md — Docker Compose 骨架 (app + chromadb)、Dockerfile、requirements.txt、环境变量配置、FastAPI 应用骨架
- [x] 01-02-PLAN.md — 文档解析 (PDF/MD/TXT)、中文分块、DashScope Embedding 生成、ChromaDB 存储、POST /documents/upload 端点
- [ ] 01-03-PLAN.md — GET /health 端点 (含 ChromaDB + DashScope 连通检查)、GET /documents 文档列表端点

### Phase 2: RAG 查询 API
**Goal**: 用户可通过符合 `接口规范.md` 的 OpenAI 兼容接口向知识库提问，并获得基于检索内容的中文回答
**Depends on**: Phase 1
**Requirements**: QUERY-01, QUERY-02, QUERY-03, QUERY-04
**Plans**: 2 plans
**Success Criteria** (what must be TRUE):
  1. `POST /v1/chat/completions` 接受 `{model, messages}` 请求体，返回符合接口规范的 `choices[0].message.content` 结构（含 `usage` 字段）
  2. 查询流程经由 LangGraph 编排：检索相关文档块 → 相关性评估 → 调用 Qwen LLM 生成回答
  3. 当知识库中存在相关文档时，回答内容准确引用文档内容，不产生幻觉
  4. 当知识库中无相关文档时，接口返回礼貌的中文兜底回复，而非捏造答案

Plans:
- [x] 02-01-PLAN.md — LangGraph RAG graph: state schema, retrieve/grade/generate nodes, compiled StateGraph
- [x] 02-02-PLAN.md — FastAPI /v1/chat/completions endpoint with Pydantic schemas matching 接口规范.md

### Phase 3: 评测数据集生成
**Goal**: 用户可触发从知识库文档自动生成评测 Q&A 对，并下载符合数据集提交规范的 ZIP 压缩包
**Depends on**: Phase 2
**Requirements**: DATASET-01, DATASET-02, DATASET-03, DATASET-04
**Plans**: TBD
**Success Criteria** (what must be TRUE):
  1. `POST /dataset/generate` 成功触发生成任务，对所有已摄入文档生成 Q&A 对
  2. 每条生成的 Q&A 对包含所有必填字段：`id`、`task_type`、`category`、`user_prompt`、`answer_type`、`correct_answer`，类型为 `chat:text` / `free_form`
  3. 生成的答案来源于对应文档块内容，可追溯到源文档，无幻觉内容
  4. 导出的 ZIP 文件包含 `evaluation_data.json` 与空 `attachments/` 目录，结构符合 `数据集提交指南.md` 规范

Plans:
- [ ] 03-01: Q&A 对生成逻辑（基于文档块调用 LLM，保证接地性）
- [ ] 03-02: 数据集导出为符合提交规范的 ZIP 格式与 `/dataset/generate` 端点

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 基础设施与文档摄入 | 2/3 | In Progress|  |
| 2. RAG 查询 API | 2/2 | Complete | 2026-04-16 |
| 3. 评测数据集生成 | 0/2 | Not started | - |
