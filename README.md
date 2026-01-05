# Claude Code 评分工具 (cc-eval)

这是一个为 Claude Code 设计的评分工具，通过 **MCP (Model Context Protocol)** 协议集成，提供智能的会话质量评估。

## 1. 功能特性

本工具提供 3 个核心 MCP 工具，模型会根据自然语言自动选择和填充参数。

### 🛠️ evaluate_session
评估会话表现，包括首次完成度、时间、交互次数、代码质量等 6 个维度。

- **session_id** (string, 可选): 指定会话 ID。不填则默认评估**当前最新会话**。
- **project_path** (string, 可选): 限定项目路径。
- **include_agents** (boolean, 默认 false): 是否包含 Sub-Agent 的交互记录。
- **first_completed** (boolean, 可选): 手动指定"首次请求是否完成需求"。不填则由算法自动判断（关键词）。
- **format** (string, 默认 "table"): 输出格式。可选值: `table`, `json`, `markdown`。

### 🛠️ list_sessions
列出历史会话记录，用于查找旧会话 ID。

- **limit** (integer, 默认 10): 返回的会话数量。
- **project_path** (string, 可选): 仅列出指定项目的会话。

### 🛠️ get_session_info
获取会话的元数据（时间、行数、摘要），不执行耗时的代码评分。

- **session_id** (string, 必需): 目标会话 ID。

---

**评分维度说明：**
- **首次需求完成度**：是否一次性解决问题 (关键词检测 + 交互分析)
- **首次响应时间**：首个 AI 回复的延迟 (目标 < 5s)
- **提示词次数**：达成目标所需的交互轮数
- **总推理时间**：所有 AI 回复的累计耗时
- **代码规模**：生成代码的总行数
- **代码质量**：圈复杂度 (Radon)、可维护性指数、Lint 错误 (Flake8)

## 2. 配置方法 (Claude Code CLI)

在终端运行以下命令即可完成注册：

```bash
# 1. 安装依赖
cd /mnt/lwy/ClaudeCode
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# 2. 注册 MCP Server
claude mcp add cc-eval -- /mnt/lwy/ClaudeCode/.venv/bin/python /mnt/lwy/ClaudeCode/mcp_server.py
```

**验证配置：**
```bash
claude mcp list
```

## 3. 使用方法

配置完成后，在 Claude Code 的对话中直接使用自然语言：

- **评分**：`帮我评分`
- **查询**：`列出最近的会话`
- **详情**：`查看会话 [ID] 的详情`

## 4. 目录结构

```
ClaudeCode/
├── mcp_server.py           # MCP Server 入口 (核心)
├── cc_evaluator/           # 评分核心逻辑模块
├── cc_eval.py              # 命令行调试入口 (可选)
├── requirements.txt        # 项目依赖
├── ARCHITECTURE.md         # 架构文档
└── README.md               # 使用说明
```
