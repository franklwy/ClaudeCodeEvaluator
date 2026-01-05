# Claude Code Evaluator (cc-eval)

> 专为 Claude Code 打造的会话质量评分工具，基于 **MCP (Model Context Protocol)** 协议集成。

通过多维度分析（需求完成度、代码质量、响应时间等），帮助开发者量化评估 AI 编程助手的表现。

## 功能特性

本工具提供 3 个核心 MCP 工具，模型会根据你的自然语言指令自动调用：

### 1. evaluate_session (核心)
全方位评估会话表现。
- **调用示例**: "帮我评分", "评估当前会话", "看看这次表现如何"
- **评分维度**:
  - **首次完成度**: 是否一次性解决问题（基于关键词检测）
  - **响应速度**: 首次响应耗时 & 总耗时
  - **交互效率**: 达成目标所需的交互轮数
  - **代码质量**: 圈复杂度(Radon) + 可维护性 + Lint检查(Flake8)

### 2. list_sessions
列出历史会话，方便查找旧记录。
- **调用示例**: "列出最近的会话", "查看历史记录"

### 3. get_session_info
查看会话元数据（不执行耗时评分）。
- **调用示例**: "查看这个会话的详情"

---

## 快速开始

### 前置要求
- Python 3.10 或更高版本
- Claude Code CLI

### 安装配置

在项目根目录下运行以下命令（自动配置绝对路径）：

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# 2. 注册 MCP Server (使用当前路径)
claude mcp add cc-eval -- $(pwd)/.venv/bin/python $(pwd)/mcp_server.py
```

---

## 使用指南

配置完成后，在 Claude 的对话框中像与同事交谈一样使用：

| 你想做什么 | 你可以说... |
|------------|-------------|
| **评估当前工作** | "给这次会话打个分" <br> "评估一下刚才的表现" |
| **查找历史** | "列出最近的 5 个会话" <br> "我昨天做了什么？" |
| **指定格式** | "用 JSON 格式输出评分报告" <br> "生成 Markdown 格式的评分表" |
| **指定参数** | "评估会话 abc-123，忽略 Agent 记录" |

---

## 常见问题

**Q: "列出最近的会话" 没有反应？**
A: 请确保 MCP Server 已正确注册。运行 `claude mcp list` 查看状态。如果状态正常但无反应，尝试更明确的指令："请调用 list_sessions 工具"。

**Q: 评分报告中的"首次完成度"是如何判断的？**
A: 工具会自动分析后续对话中是否出现"修改"、"错误"、"bug"等关键词。如果出现，判定为未一次性完成。你可以通过参数 `first_completed=true` 手动覆盖此判断。

**Q: 如何查看工具的运行日志？**
A: 日志保存在项目目录下的 `cc_eval.log` 文件中。

---

## 项目结构

```text
.
├── mcp_server.py           # MCP Server 入口 (FastMCP)
├── cc_evaluator/           # 评分核心逻辑
│   ├── evaluators/         # 评分器 (时间、代码、交互等)
│   ├── parser/             # 日志解析器
│   └── reporter/           # 报告生成器
├── requirements.txt        # 项目依赖
├── ARCHITECTURE.md         # 架构设计文档
└── cc_eval.log             # 运行日志
```
