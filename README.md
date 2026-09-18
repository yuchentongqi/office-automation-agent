# 办公自动化 Agent

Supervisor + 子 Agent 协作的办公自动化系统。用自然语言下达指令，系统自动识别意图，调度对应的子 Agent，集成飞书日历、飞书消息、Agent Mail 邮件、任务提取与周报生成。

第五个小项目，因为我发现有时候表述不清，agent追问时候再回答会没有记忆，所以我加了个简单的三轮记忆，能有效避免所谓的回答agent问题结果反应不出结果，然后这个办公的邮件我用的
是agent mail，我觉得相当nice，很轻松连接了。

##  功能

-  **Supervisor 调度**：主管 Agent 识别意图，路由到子 Agent
-  **日历管理**：通过飞书日历 API 创建、查询日程
-  **消息发送**：通过飞书 API 发送消息
-  **邮件处理**：接入 Agent Mail，支持查看、搜索、读取、发送邮件
-  **任务管理**：从邮件提取待办事项，存入本地数据库
-  **周报生成**：汇总本周日程和任务，生成 Markdown 周报
-  **多轮记忆**：保留最近 3 轮对话，支持指代追问
-  **回复审核**：独立节点校验回复，防止编造

##  架构

```
用户问题
   ↓
Supervisor（意图识别）
   ├── 日历 Agent → 飞书日历 API
   ├── 消息 Agent → 飞书消息 API
   ├── 邮件 Agent → Agent Mail CLI + 任务工具
   ├── 周报 Agent → 汇总数据 + LLM 生成
   └── 闲聊节点
   ↓
回复审核 → 返回用户
```

##  快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yuchentongqi/office-automation-agent.git
cd office-automation-agent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装 Agent Mail CLI

```bash
npm install -g @tencent-qqmail/agently-cli
agently-cli auth login
```

### 5. 配置环境变量

在项目根目录创建 `.env`：

```
DASHSCOPE_API_KEY=sk-你的阿里云百炼Key
MODEL_NAME=qwen3.7-flash
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

FEISHU_APP_ID=cli_你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
```

飞书应用需要在 [飞书开放平台](https://open.feishu.cn) 创建，并开通日历、消息相关权限。

### 6. 初始化数据库

```bash
python scripts/init_db.py
```

### 7. 启动

```bash
python app.py
```

浏览器打开 `http://127.0.0.1:7860`。

##  使用示例

| 问题 | 意图 |
|---|---|
| 看看我最近的邮件 | 邮件 |
| 搜索包含"项目"的邮件 | 邮件 |
| 从邮件里提取任务 | 任务 |
| 看看我最近的任务 | 任务 |
| 明天下午3点安排一个产品评审会 | 日历 |
| 今天有什么日程安排？ | 日历 |
| 生成本周周报 | 周报 |

##  项目结构

```
office-automation-agent/
├── app.py                  # Gradio 界面入口
├── agent/
│   ├── graph.py            # LangGraph 工作流编排
│   ├── nodes.py            # Supervisor + 各子 Agent 节点
│   ├── tools.py            # 飞书日历/消息工具
│   ├── email_tools.py      # Agent Mail 邮件工具
│   ├── task_tools.py       # 任务提取与管理工具
│   ├── report_tools.py     # 周报生成工具
│   └── feishu_api.py       # 飞书 API 封装
├── scripts/
│   └── init_db.py          # 初始化任务数据库
├── reports/                # 生成的周报（不传 Git）
├── .gitignore
├── requirements.txt
└── README.md
```

##  技术栈

| 组件 | 用途 |
|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | 多 Agent 工作流编排 |
| [LangChain](https://github.com/langchain-ai/langchain) | Agent 与工具集成 |
| [通义千问](https://bailian.console.aliyun.com/) | 大语言模型 |
| [飞书开放平台](https://open.feishu.cn) | 日历与消息 API |
| [Agent Mail](https://agent.qq.com) | AI Agent 专属邮箱 |
| [Gradio](https://gradio.app/) | Web 界面 |
| [SQLite](https://www.sqlite.org/) | 本地任务存储 |

##  License

MIT
