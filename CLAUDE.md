# Smart Trip Planner (智能行程规划助手)

## 项目简介

Smart Trip Planner 是一个基于 AI Agent × 腾讯地图 × MCP 的智能旅行规划工具。用户通过自然语言描述旅行需求，AI 自动解析意图并调用腾讯地图 API 完成 POI 检索、路径规划、可视化展示，输出完整的行程方案。

该项目参与腾讯位置服务开发者征文大赛（2026年5月），作为展示 AI Agent、MCP 协议与腾讯地图能力结合的 Demo。

### 技术栈

- **后端**: Python FastAPI
- **AI 层**: DeepSeek-V3 / 硅基流动
- **地图服务**: 腾讯位置服务 WebService API (POI/地理编码/距离矩阵/路线规划)
- **协议**: MCP (Model Context Protocol)
- **前端**: HTML + 腾讯地图 JS API GL

### 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── core/
│   │   ├── config.py        # 全局配置管理 (Pydantic Settings)
│   │   ├── cache.py         # 缓存层
│   │   └── exceptions.py    # 自定义异常
│   ├── models/              # 数据模型
│   ├── services/            # 业务逻辑 (AI解析/POI服务/路径优化/报告生成)
│   ├── api/v1/              # API 路由 (trip/poi/health)
│   └── conversation/        # 多轮对话 Agent
├── tests/
├── data/
└── scripts/
```

## 为什么用 Claude Code 开发

1. **快速迭代**: Claude Code 能够直接读取、理解和修改代码库，减少了上下文切换成本，适合在有限时间内快速开发 Demo 项目。

2. **AI Agent × MCP 契合度**: 本项目本身就是 MCP 协议在旅行规划场景的实践，而 Claude Code 原生支持 MCP 工具链，在开发中天然对齐架构思路。

3. **多语言/多文件协作**: 项目涉及 Python 后端、前端 HTML/JS、文档等多类型文件，Claude Code 的跨文件上下文理解能力使这类协作更高效。

4. **代码质量**: Claude Code 能自动发现硬编码、配置分散等问题，帮助保持代码整洁和可维护。

## 开发过程记录

### 立项阶段 (2025-04-13)
- 完成项目立项文档、产品设计文档、后端系分文档
- 确定技术栈：FastAPI + DeepSeek + 腾讯地图 + MCP

### 后端开发 (2025-04-14 ~ 04-16)
- FastAPI 项目骨架搭建，全局配置管理
- POI 检索服务、路径优化算法
- AI 意图解析服务、LLM Provider 抽象层
- 多轮对话 Agent 架构

### 前端开发 (2025-04-17 ~ 04-19)
- 腾讯地图 JS API GL 前端可视化
- 路线标注、景点标记、交互功能

### LLM 对接 (2025-04-20 ~ 04-21)
- MCP 工具链封装，支持 DeepSeek/硅基流动/OpenAI 多 Provider

### Demo 完善 (2025-04-22 ~ 04-25)
- Bug 修复、体验优化

### 配置优化 (2025-05-08)
- **硬编码清理**: 将 `main.py` 中硬编码的 `version="1.1.0"` 改为从 `settings.APP_VERSION` 读取，消除版本号不一致风险
- **日志级别动态化**: `logging.INFO` 改为根据 `settings.DEBUG` 动态设置，开发环境输出 DEBUG 日志，生产环境保持 INFO
- **CORS 默认值**: 为 `CORS_ORIGINS` 添加 Pydantic 默认值，消除 `main.py` 中的 `getattr` fallback 逻辑
