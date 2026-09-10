> 本文档由 AI 翻译自英文原文，可能存在疏漏。以准确性为准时请参阅[英文原版](../../../00-course-setup/README.md)。

# 课程环境准备

## 简介

这一课讲的是如何运行本课程的代码示例。所有课程使用同一套环境：Python 3.12、一次 `pip install`，以及一个指向 OpenAI 兼容模型接口的 `.env` 文件。除了模型服务商本身，不需要任何云账号。

## 克隆或 Fork 本仓库

先克隆或 fork 这个 GitHub 仓库。Fork 会给你一份属于自己的副本，可以随意折腾。

点击仓库页面上的 **fork** 按钮，然后选择要 fork 到哪个仓库：

![Select fork repository](../../../00-course-setup/images/select-fork-repository.png)

## 前置条件

- Python 3.12 或更高版本
- 一个支持工具调用的 OpenAI 兼容接口的 API key（默认配置使用 [DeepSeek](https://platform.deepseek.com/)）
- Node.js LTS，供第 11 课（github-mcp 应用）和第 17 课使用（两者都会用 `npx` 启动 MCP 服务器）

## 安装步骤

### 第 1 步：创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
# Windows: py -3.12 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
# If PowerShell reports that scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once,
# or use `.venv\Scripts\activate.bat` from cmd.
pip install -r requirements.txt
```

### 第 2 步：创建你的 `.env` 文件

```bash
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
```

打开 `.env`，填入四个必需的值：

```text
LLM_BASE_URL="https://api.deepseek.com/v1"
LLM_API_KEY="sk-..."
LLM_MODEL="deepseek-v4-pro"
LLM_EXTRA_BODY='{"thinking": {"type": "disabled"}}'
```

`LLM_EXTRA_BODY` 是随每次请求一起发送的 JSON 对象；DeepSeek 的思考型模型会拒绝结构化输出所需的强制工具调用，所以这里把思考模式关掉（如果你的服务商不接受未知字段，把它留空）。

`.env` 已经写进 `.gitignore`，所以你的 key 只会留在本机。

### 第 3 步：检查你的接口

```bash
python scripts/check_endpoint.py
```

这个脚本会发出四个很小的请求（`VISION_MODEL` 为空时是三个），并打印出这样一张表：

```text
Endpoint: https://api.deepseek.com/v1
Model:    deepseek-v4-pro

capability  result    used by lessons
chat        PASS      all lessons
tools       PASS      01, 03-05, 07-13, 16-18 (create_agent needs tool calling)
structured  PASS      03, 07, 08 (structured output forces a tool call; DeepSeek thinking models need LLM_EXTRA_BODY to disable thinking)
vision      PASS      10 (expense demo), 15 (browser-use) — optional, set VISION_* to enable

Ready: this endpoint supports everything the course requires.
```

`chat` 和 `tools` 必须通过。如果 `tools` 失败，说明这个模型不支持函数调用，换一个模型。如果只有 `structured` 失败，脚本会给出提示：在 DeepSeek 上按第 2 步设置 `LLM_EXTRA_BODY`。

### 第 4 步：运行一个 notebook

```bash
jupyter notebook
```

打开 `01-intro-to-ai-agents/code_samples/01-python-langchain-agent.ipynb`，从上到下逐个运行单元格。每个 notebook 开头都是同一段加载 `.env`、构建模型客户端的代码：

```python
import json
import os
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())
llm = ChatOpenAI(
    model=os.environ["LLM_MODEL"],
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    extra_body=json.loads(os.environ.get("LLM_EXTRA_BODY") or "null"),
)
```

## 换用其他模型服务商

任何实现了 OpenAI Chat Completions API 且支持工具调用的接口都可以用，改一下 `LLM_*` 的值即可：

| 服务商 | `LLM_BASE_URL` | `LLM_MODEL` 示例 | `LLM_EXTRA_BODY` | 说明 |
|---|---|---|---|---|
| DeepSeek（默认） | `https://api.deepseek.com/v1` | `deepseek-v4-pro` | 按上文设置 | 同一接口也提供第 10、15 课使用的视觉模型。 |
| OpenAI | `https://api.openai.com/v1` | `gpt-5-mini` | 留空 | 也可用作 `VISION_*` 接口。 |
| MiniMax | `https://api.minimax.io/v1` | `MiniMax-M3` | 留空 | 上下文窗口很大。 |
| Ollama（本地） | `http://localhost:11434/v1` | `qwen3:8b` | 留空 | 设置 `LLM_API_KEY="ollama"`。多智能体课程建议用 7B 以上的模型。 |
| vLLM（自建） | `http://localhost:8000/v1` | 你部署的模型名 | 留空 | 任何支持工具调用的模型都可以。 |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-5.3-flash` | 留空 | `LLM_EXTRA_BODY` 留空；`glm-4.5v` 可作为 `VISION_MODEL`。 |

换完之后再跑一次 `python scripts/check_endpoint.py`。

### 可选：第 10、15 课用的视觉模型

第 10 课的报销示例要读取一张收据图片，第 15 课要靠截图驱动浏览器。DeepSeek 在同一个接口上提供 `deepseek-v4-flash-vision-exp`，因此 `.env.example` 里的 `VISION_*` 默认值不需要额外的 key 就能让两课都跑起来（`VISION_API_KEY` 留空时会复用 `LLM_API_KEY`）。任何支持图片输入的接口同样可用：

```text
VISION_BASE_URL="https://api.openai.com/v1"
VISION_API_KEY="sk-..."
VISION_MODEL="gpt-5-mini"
```

如果想让这两课走纯文本路径，把 `VISION_MODEL` 留空即可。

### 可选：第 17 课用的本地模型

第 17 课会构建一个完全跑在你本机上的智能体，用的是 [Ollama](https://ollama.com/)。装好 Ollama 之后：

```bash
ollama pull qwen3:8b
ollama serve      # skip this if Ollama already runs as a background service
```

`.env` 里的 `LOCAL_LLM_BASE_URL` 和 `LOCAL_LLM_MODEL` 已经指向 Ollama 的默认端口和这个模型。如果机器可用内存不足 8 GB，改拉 `qwen3:1.7b`，并把 `LOCAL_LLM_MODEL` 改成对应的值。

### 可选：第 15 课用的浏览器

```bash
pip install browser-use playwright
playwright install chromium
```

## 向量检索

第 05、11、16、17 课使用 [Chroma](https://www.trychroma.com/) 作为本地向量库。它在进程内运行，不需要服务端，也不需要嵌入向量 API。两分钟的入门介绍见 [vector-search-setup.md](./vector-search-setup.md)。

## 配置 VS Code

安装 Python 和 Jupyter 扩展，打开仓库目录，选择 `.venv` 解释器（**Python: Select Interpreter**）。之后 notebook 就能在 VS Code 里跑，并使用同一个 `.env`。

## 常见问题排查

### `check_endpoint.py` 报 `tools FAIL`

说明该模型不支持函数调用。换一个支持的模型（上表中每个服务商都列了一个）。

### `401 Unauthorized`

`.env` 里的 key 不对，或者它属于另一个服务商，与 `LLM_BASE_URL` 不匹配。检查这两个值是否对得上。

### macOS 上的 SSL 证书校验错误

如果你从 python.org 安装了 Python 并遇到 `SSL: CERTIFICATE_VERIFY_FAILED`，运行 Python 自带的证书安装脚本：

```bash
# Replace 3.XX with your installed Python version (for example 3.12)
/Applications/Python\ 3.XX/Install\ Certificates.command
```

### notebook 内核读不到 `.env`

`find_dotenv()` 会从 notebook 所在目录向上查找，所以 `.env` 必须放在仓库根目录，而不是某一课的文件夹里。

## 卡在某个地方？

在本仓库提一个 issue，写清课程编号、出错的单元格，以及完整的报错信息。

## 下一课

[AI 智能体入门与应用场景](../01-intro-to-ai-agents/README.md)
