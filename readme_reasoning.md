<<<<<<< HEAD
# 酒店服务与退票 Reasoning Agent

针对用户的酒店服务智能助手，专注于处理酒店换房/退租和退票等需求，支持图像识别和多渠道交互。集成高德地图MCP服务获取酒店信息，使用通义千问API分析用户输入，并通过WebSocket实现实时反馈。

## 项目概述

本项目是一个基于LLM的推理代理系统，旨在帮助用户处理酒店服务和退票问题。系统通过网页接口接收用户请求，进行智能推理并提供解决方案。系统采用LangGraph框架构建推理流程，确保处理逻辑清晰且可扩展。

系统集成了通义千问API的图像理解能力，能够从酒店预订单、机票等图片中自动提取关键信息。同时，系统还集成了高德地图MCP服务，可以获取酒店的详细信息和联系方式，为用户提供更全面的退票服务。

系统还实现了WebSocket通信机制，能够在处理过程中实时向前端发送反馈信息，提升用户体验。同时，针对退票请求，系统会生成结构化的处理提示并存储到MongoDB中，供后续的calling agent使用。

## 技术栈

- Python 3.9+
- FastAPI (后端框架)
- LangChain/LangGraph (LLM框架)
- OpenAI API (大语言模型)
- Poetry (依赖管理)
- Conda (环境管理)
- MongoDB (NoSQL数据库，存储对话历史和酒店信息)
- 通义千问API (图像理解和文本分析)
- 高德地图API (获取酒店信息)
- WebSocket (实时通信)
- Spacy & Transformers (NLP处理)

## 项目结构

```
.
├── README.md                 # 项目说明文档
├── pyproject.toml           # Poetry配置文件
├── .env                     # 环境变量配置
├── .env.example             # 环境变量示例
├── agent/                   # 代理主目录
│   ├── app/                 # 应用代码
│   │   ├── __init__.py     # 包初始化
│   │   ├── main.py         # FastAPI应用入口
│   │   ├── reasoning_module.py # 核心推理模块
│   │   ├── agents/         # 代理模块
│   │   │   ├── reasoning_agent.py  # 推理代理
│   │   │   ├── reasoning_graph.py  # 推理流程图
│   │   │   └── summary_agent.py    # 总结代理
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务服务
│   │   │   ├── agent_service.py    # 代理服务
│   │   │   ├── db_service.py       # 数据库服务
│   │   │   ├── gaode_mcp_service.py # 高德地图MCP服务
│   │   │   ├── image_service.py    # 图像服务
│   │   │   ├── qwen_text_service.py # 通义千问文本服务
│   │   │   ├── qwen_vision_service.py # 通义千问视觉服务
│   │   │   └── websocket_service.py # WebSocket服务
│   │   └── utils/          # 工具函数
│   ├── examples/           # 示例代码
│   │   └── test_reasoning_agent.py # 推理代理测试
│   └── tests/              # 测试目录
```

## 功能特点

- 基于LangGraph的智能推理处理酒店换房/退租需求和退票请求
- 退票请求信息完整性检查，自动提示用户补充缺失信息
- 酒店信息检索和验证
- 高德地图MCP集成，获取酒店联系方式等信息
- 退票流程处理和信息收集，并存储到MongoDB中
- 用户意图识别与澄清
- WebSocket实时反馈：
  - 在处理过程中向前端发送不同类型的反馈信息
  - 支持错误反馈、信息不完整提示、退票确认等多种消息类型
  - 提供结构化的元数据，便于前端进行个性化展示
- 退票处理prompt生成：
  - 自动将用户的退票需求转换为结构化的prompt
  - 将prompt存储到MongoDB中，供后续calling agent使用
  - 包含退票请求的目的、酒店信息、操作步骤和注意事项
- 图像理解功能：
  - 通过通义千问API自动识别酒店预订单和机票信息
  - 支持中英文文本提取
  - 结构化信息提取（酒店名称、预订日期、订单号等）
- 文本分析功能：
  - 使用通义千问API分析用户文本输入
  - 自动提取退票相关信息（酒店名称、订单号、入住日期、客人姓名）

## 安装与运行

### 环境配置

```bash
# 创建conda环境
conda create -n hotel-agent python=3.9
conda activate hotel-agent

# 安装Poetry
pip install poetry

# 安装依赖
poetry install
```

### 配置环境变量

`.env`文件配置以下变量：

```
# API Keys
DASHSCOPE_API_KEY=your_dashscope_api_key

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=hotel_db
DB_PATH=./data/hotel_db

# 高德地图API配置
GAODE_API_KEY=your_gaode_api_key
```

### 运行应用

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 使用说明

访问 http://localhost:8000/docs 查看API文档和测试接口。

## 开发计划

- [x] 项目基础架构搭建
- [x] 推理代理核心逻辑实现
- [x] 通义千问API图像理解集成
- [x] 通义千问API文本分析集成
- [x] 退票功能实现，包括信息完整性检查
- [x] 高德地图MCP集成，获取酒店信息
- [x] 数据存储优化，解决数据目录冲突
- [x] WebSocket集成，实现实时反馈
- [x] 退票处理prompt生成与存储
- [ ] 前端界面优化
- [ ] 部署与性能优化
- [ ] 酒店信息数据库扩展
- [ ] 对话状态管理优化
- [ ] 用户界面开发
=======
# Customer_Agent_Overall
>>>>>>> 5c430baffbc720c666a30e28b47aef8a155e496b
