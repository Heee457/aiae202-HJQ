> 本文档由 AI 翻译自英文原文，可能存在疏漏。以准确性为准时请参阅[英文原版](../../../02-explore-agentic-frameworks/README.md)。

# 探索 AI 智能体框架

AI 智能体框架是一类软件平台，用来简化 AI 智能体的创建、部署和管理。它们为开发者提供预制组件、抽象层和工具，让复杂 AI 系统的开发变得顺畅。

这些框架把 AI 智能体开发中的常见难题标准化，让开发者可以专心处理自己应用中独特的部分。它们提升了构建 AI 系统时的可扩展性、易用性和效率。

## 引言 

本课涵盖以下内容：

- 什么是 AI 智能体框架，它们让开发者能做到什么？
- 团队如何用它们快速做原型、迭代并提升智能体的能力？
- 相比裸用 SDK，智能体框架能带给你什么？
- LangChain、LangGraph 和其他开源框架之间如何比较？
- 什么时候该动用基于图的工作流？

## 学习目标

本课的目标是帮助你理解：

- AI 智能体框架在 AI 开发中扮演的角色。
- 如何借助 AI 智能体框架构建智能体。
- AI 智能体框架带来的关键能力。
- 直接调用模型 API、使用 `create_agent` 和构建 `StateGraph` 工作流三者之间的区别。

## 什么是 AI 智能体框架，它们让开发者能做什么？

传统 AI 框架可以帮你把 AI 集成进应用，并从以下几个方面让应用变得更好：

- **个性化**：AI 可以分析用户行为和偏好，提供个性化的推荐、内容和体验。
例如：Netflix 这类流媒体服务用 AI 根据观看历史推荐影视剧，提升用户参与度和满意度。
- **自动化与效率**：AI 可以自动完成重复性任务、理顺工作流程、提升运营效率。
例如：客服应用用 AI 驱动的聊天机器人处理常见咨询，缩短响应时间，把人工客服解放出来处理更复杂的问题。
- **更好的用户体验**：AI 可以提供语音识别、自然语言处理、预测性文本输入等智能特性，从整体上改善用户体验。
例如：Siri 和 Google Assistant 这类虚拟助手用 AI 理解并响应语音指令，让用户更容易与设备交互。

### 听起来都挺好，那我们为什么还需要 AI 智能体框架？

AI 智能体框架不只是 AI 框架。它们的目标是让你能够创建智能体——能与用户、其他智能体以及环境交互，以达成特定目标。这类智能体可以表现出自主行为，做出决策，并适应变化的条件。我们来看看 AI 智能体框架带来的几项关键能力：

- **智能体协作与协调**：支持创建多个 AI 智能体，让它们协同工作、彼此通信、相互配合，共同解决复杂任务。
- **任务自动化与管理**：提供多步骤工作流自动化、任务分派以及智能体之间动态任务管理的机制。
- **上下文理解与适应**：让智能体具备理解上下文、适应环境变化、依据实时信息做决策的能力。

总的来说，智能体让你能做更多事，把自动化推向新的层次，构建出能适应环境并从中学习的、更智能的系统。

## 如何快速做原型、迭代并提升智能体的能力？

这是一个变化很快的领域，但大多数 AI 智能体框架都有一些共通之处能帮你快速做原型和迭代，也就是模块化组件、协作工具和实时学习。我们逐个来看：

- **使用模块化组件**：AI SDK 提供预制组件，例如 AI 与记忆连接器、用自然语言或代码插件实现的函数调用、提示词模板等等。
- **善用协作工具**：给智能体设计明确的角色和任务，从而测试和打磨协作式工作流。
- **实时学习**：建立反馈回路，让智能体从交互中学习并动态调整自己的行为。

### 使用模块化组件

LangChain 这类 SDK 提供了预制组件，例如聊天模型客户端、工具定义和智能体管理。

**团队可以怎么用**：团队可以把这些组件快速拼装成一个可运行的原型，不必从零开始，从而快速实验和迭代。

**实际怎么运作**：你可以用聊天模型客户端对接任何兼容 OpenAI 的接口地址，用检查点存储器（checkpointer）保存和读取对话历史，用系统提示词塑造智能体与用户交互的方式——这些组件都不用你自己从头造。

**示例代码**。我们来看一个例子，用 LangChain 配合 `ChatOpenAI`，让模型通过工具调用来响应用户输入：

``` python
# LangChain Python Example

import json
import os

from dotenv import find_dotenv, load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI


# Define a sample tool function to book travel
@tool
def book_flight(date: str, location: str) -> str:
    """Book travel given location and date."""
    return f"Travel was booked to {location} on {date}"


load_dotenv(find_dotenv())

llm = ChatOpenAI(
    model=os.environ["LLM_MODEL"],
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    extra_body=json.loads(os.environ.get("LLM_EXTRA_BODY") or "null"),
)
agent = create_agent(
    llm,
    tools=[book_flight],
    system_prompt="Help the user book travel. Use the book_flight tool when ready.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "I'd like to go to New York on January 1, 2025"}]}
)
print(result["messages"][-1].content)
# Example output: Your flight to New York on January 1, 2025, has been successfully booked. Safe travels! ✈️🗽
```

从这个例子里你能看到，框架如何从用户输入中提取关键信息——比如订票请求中的目的地和日期——并把它变成对你 `book_flight` 函数的一次调用。模型需要的全部信息，就是工具的文档字符串和类型注解。这种模块化的方式让你可以专注于高层逻辑。

### 善用协作工具

LangChain 这类框架便于创建多个协同工作的智能体。

**团队可以怎么用**：团队可以给智能体设计明确的角色和任务，从而测试和打磨协作式工作流，提升整个系统的效率。

**实际怎么运作**：你可以组建一支智能体团队，每个智能体各司其职，比如数据检索、分析或决策。这些智能体彼此通信、共享信息，共同达成一个目标，例如回答用户的问题或完成一项任务。

**示例代码（LangChain）**：

```python
# Creating multiple agents that work together using LangChain
# llm: the ChatOpenAI client from the example above

from langchain.agents import create_agent
from langchain.tools import tool


@tool
def retrieve_tool(query: str) -> str:
    """Retrieve raw records for a query from the data store."""
    return "Q4 sales: Oct 120k, Nov 135k, Dec 190k"


@tool
def analyze_tool(data: str) -> str:
    """Compute summary statistics for a block of data."""
    return f"Analyzed: {data}"


# Data Retrieval Agent
agent_retrieve = create_agent(
    llm,
    tools=[retrieve_tool],
    system_prompt="Retrieve relevant data using available tools.",
)

# Data Analysis Agent
agent_analyze = create_agent(
    llm,
    tools=[analyze_tool],
    system_prompt="Analyze the retrieved data and provide insights.",
)

# Run agents in sequence on a task
retrieval_result = agent_retrieve.invoke(
    {"messages": [{"role": "user", "content": "Retrieve sales data for Q4"}]}
)["messages"][-1].content
analysis_result = agent_analyze.invoke(
    {"messages": [{"role": "user", "content": f"Analyze this data: {retrieval_result}"}]}
)["messages"][-1].content
print(analysis_result)
```

上面这段代码展示了如何创建一个由多个智能体协作完成的数据分析任务。每个智能体承担一项特定职能，通过协调这些智能体来完成任务、得到想要的结果。给智能体设定专门的角色，可以提升任务的效率和表现。

### 实时学习

更进阶的框架提供实时理解上下文并作出适应的能力。

**团队可以怎么用**：团队可以建立反馈回路，让智能体从交互中学习并动态调整行为，从而持续改进和打磨能力。

**实际怎么运作**：智能体可以分析用户反馈、环境数据和任务结果，据此更新知识库、调整决策算法，随时间推移不断提升表现。这种迭代式的学习过程让智能体能适应变化的条件和用户偏好，提升整个系统的有效性。

## LangChain 与 LangGraph

本课程用 **LangChain 1.x** 构建智能体，用 **LangGraph 1.x** 构建工作流。它们是同一套技术栈的两层：`create_agent` 建立在 LangGraph 之上，所以你从 LangChain 起步的智能体，可以在不重写工具的前提下长成一张自定义的图。

**适用场景**：构建具备工具调用、多轮对话、结构化输出、人工确认环节和显式多步骤工作流的生产级 AI 智能体。

以下是贯穿整门课程你会用到的核心概念：

- **聊天模型**。`ChatOpenAI` 讲的是 OpenAI Chat Completions 协议，因此同一份代码可以跑在 DeepSeek、OpenAI、本地 Ollama 服务或任何其他兼容的接口地址上。供应商是配置项（`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`），不是代码。
- **工具**。用 `@tool` 装饰的普通 Python 函数。文档字符串成为模型读到的描述；类型注解成为参数结构定义。
- **智能体**。`create_agent` 把聊天模型、工具和系统提示词组合成一个工具调用循环：调用模型，执行它要求的工具，把结果喂回去，如此反复，直到模型给出文字答复。
- **中间件**。在模型或工具调用之前或之后运行的钩子。内置的 `HumanInTheLoopMiddleware` 会在指定工具执行前暂停智能体，让人来批准或拒绝（第 04 课和第 06 课用到了它）。
- **检查点存储器**。`InMemorySaver` 这类检查点存储器会在每一步之后保存对话，以 `thread_id` 为键。复用同一个 id 可以接着之前的对话；换一个新 id 则重新开始。
- **`StateGraph`**。LangGraph 的工作流构建器：你声明一份带类型的状态、若干节点（Python 函数）和边（包括条件边），然后把它编译成一张可运行的图。第 08 课就是这样构建多智能体工作流的。
- **流式输出**。每个智能体和图都可以流式运行；`stream_mode="messages"` 会在模型 token 到达时逐个产出。

下面三段代码与本课的 notebook 一致。

**创建一个带工具的智能体：**

```python
import json
import os
from typing import Annotated

from dotenv import find_dotenv, load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())

llm = ChatOpenAI(
    model=os.environ["LLM_MODEL"],
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    extra_body=json.loads(os.environ.get("LLM_EXTRA_BODY") or "null"),
)


@tool
def check_destination_availability(
    destination: Annotated[str, "The destination to check availability for"]
) -> str:
    """Check if a vacation destination is currently available for booking."""
    available = {"Barcelona": True, "Tokyo": True, "Cape Town": False}
    is_available = available.get(destination, False)
    return f"{destination} is {'available' if is_available else 'not available'} for booking."


agent = create_agent(
    llm,
    tools=[check_destination_availability],
    system_prompt="You are a travel booking agent. Always check availability before recommending a destination.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "Is Tokyo available?"}]})
print(result["messages"][-1].content)
```

**用检查点存储器和会话线程记住一段对话：**

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    llm,
    tools=[check_destination_availability],
    system_prompt="You are a travel booking agent. Always check availability before recommending a destination.",
    checkpointer=InMemorySaver(),
)
session = {"configurable": {"thread_id": "conversation-1"}}

agent.invoke({"messages": [{"role": "user", "content": "Is Barcelona available?"}]}, session)
result = agent.invoke({"messages": [{"role": "user", "content": "And what about somewhere colder?"}]}, session)
print(result["messages"][-1].content)   # the agent still knows Barcelona was discussed
```

**在生成 token 的同时流式输出：**

```python
async for token, metadata in agent.astream(
    {"messages": [{"role": "user", "content": "Plan me a day trip."}]},
    session,
    stream_mode="messages",
):
    if metadata.get("langgraph_node") == "model" and getattr(token, "content", None):
        print(token.content, end="", flush=True)
print()
```

## 其他开源智能体框架

LangChain 不是唯一的选择。下面这些框架解决的是同样的问题，只是对“智能体该如何被编排”有各自不同的主张。它们都采用宽松许可协议，都能对接兼容 OpenAI 的接口地址，也都支持用 Model Context Protocol 接入工具。

| 框架 | 编排风格 | 结构化输出 | 人工确认环节 | 许可协议 | 文档 |
| --- | --- | --- | --- | --- | --- |
| **LangGraph**（配合 LangChain） | 图式编排：带类型的状态、节点和边；常见的工具调用循环用 `create_agent` | 智能体上的 `response_format=`，模型上的 `with_structured_output` | 任意节点中的 `interrupt()`；工具审批用 `HumanInTheLoopMiddleware` | MIT | [docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/overview) |
| **CrewAI** | 基于角色的团队：带角色和目标的智能体、任务，以及顺序或层级式流程 | 任务上的 `output_pydantic` / `output_json` | 任务上的 `human_input=True` | MIT | [docs.crewai.com](https://docs.crewai.com/) |
| **Pydantic AI** | 用 Pydantic 模型定义的带类型智能体；用 Pydantic Graph 表达显式状态机 | 智能体上的 `output_type=`，由 Pydantic 校验 | 延迟执行的工具调用，运行前需要审批 | MIT | [ai.pydantic.dev](https://ai.pydantic.dev/) |
| **OpenAI Agents SDK** | 智能体、智能体之间的交接、输入输出上的护栏 | 智能体上的 `output_type=` | 工具上的 `needs_approval=True`；从 `result.interruptions` 恢复 | MIT | [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) |
| **smolagents** | 以代码行动的智能体：模型写出调用工具的 Python；默认执行器在本地带限制地运行，沙箱隔离需要显式配置执行器 | 没有原生的结构定义；在 `final_answer_checks` 中校验 | 步骤回调和 `interrupt()` | Apache-2.0 | [huggingface.co/docs/smolagents](https://huggingface.co/docs/smolagents) |

读这张表时可以留意几点：

- **图、角色，还是代码。** LangGraph 要你把工作流画出来；CrewAI 要你描述一支团队；smolagents 让模型把计划写成代码。对不同类型的问题，它们各自都是合理的默认选择。
- **结构化输出已是标配。** 大多数框架都能返回一个校验过的对象而非自由文本；区别主要在于你在哪里声明这个结构。
- **人工确认环节需要持久化状态。** 暂停智能体等待审批、稍后再恢复，要求在两次请求之间保存状态。LangGraph 的检查点存储器把这件事显式化了；其他框架则在任务或工具层面处理。

## 我该选哪种方式？

在 LangChain 这套技术栈里，你有三个层次可选。它们不是竞争关系：`create_agent` 会编译成一张 LangGraph 的 `StateGraph`，而两者都通过同一个兼容 OpenAI 的客户端与模型通信。

- **裸用兼容 OpenAI 的 SDK**（`openai` 包）：你自己构造请求、从响应中解析工具调用、执行工具，并自己写循环。控制力最强，没有任何抽象，也有大量模板代码需要维护正确。
- **LangChain `create_agent`**：工具调用循环、工具结构定义的生成、记忆、结构化输出和中间件都是现成的。一次函数调用就给你一个可用于生产的智能体。
- **LangGraph `StateGraph`**：你把工作流显式地画成节点和边。当步骤顺序、分支、并行处理或长时间等待的审批需要可见、可测试，而不是交给模型自行决定时，就用它。

还是拿不准该选哪个？

### 使用场景

我们通过几个常见场景来帮你判断：

> 问：我在做一个 AI 智能体应用，想快速上手
>
> 答：`create_agent` 是很好的选择。它提供简洁、符合 Python 习惯的 API，几行代码就能定义一个带工具和指令的智能体，而且已经内置了记忆、流式输出、结构化输出和人工审批。

> 问：我需要显式控制每一步——分支、并行子任务、重试，或者一个暂停等人处理、几天后再恢复的工作流
>
> 答：`StateGraph` 最合适。每一步都是一个可以单独测试的节点，边让控制流一目了然，检查点存储器让暂停与恢复成为一等公民。

> 问：我还是搞不清，直接给我一个选项吧
>
> 答：从 `create_agent` 开始。等你觉得它不够用了，记住它会编译成一张 LangGraph 图：你的工具、模型客户端和检查点存储器可以原封不动地迁移到 `StateGraph`，不需要重写。

我们用一张表总结关键差异：

| 方式 | 关注点 | 核心概念 | 使用场景 |
| --- | --- | --- | --- |
| 裸用兼容 OpenAI 的 SDK | 直接调用模型 | 聊天补全、工具调用解析、自己写的循环 | 单次调用、实验、完全自定义的循环 |
| LangChain `create_agent` | 现成的智能体循环 | 聊天模型、工具、系统提示词、中间件、检查点存储器 | 构建 AI 智能体、工具调用、多轮对话 |
| LangGraph `StateGraph` | 显式工作流 | 带类型的状态、节点、边、`interrupt()`、检查点存储器 | 多智能体系统、分支与并行工作流、长时间等待的审批 |

## 示例代码

- Python：[LangChain 智能体](./code_samples/02-python-langchain-agent.ipynb)

## 作业：一个记得住对话的智能体

本课的 notebook 在第 01 课的智能体之上加了两样东西：一个以 `thread_id` 为键的**检查点存储器**（`InMemorySaver`），让智能体记住前面的轮次；以及一个自带状态的工具，让连续两次调用绝不返回同样的结果。请在一个**不同的领域**里构建一个多轮对话智能体，把这两点都展示出来。可以参考这些方向：菜谱挑选、健身课程排期、图书馆助手、桌游之夜策划、语言学习导师。

### 要求

1. **新建一个 notebook**，放在 `code_samples/` 目录下，命名为 `02-assignment-<你的主题>.ipynb`。开头使用与课程 notebook 相同的环境准备单元，从 `.env` 读取 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`。绝不要把 API key 直接粘贴进 notebook。
2. **用 `@tool` 定义一个查询工具**，其参数用 `Annotated[str, "..."]` 描述含义，就像 `check_destination_availability` 那样，背后是一个至少有五个条目的字典。
3. **定义一个带状态的工具**：不接收参数，用模块级变量记住上一次的结果（即 `_last_destination` 配合 `global` 的写法），使连续两次调用绝不相同。
4. **用 `create_agent` 创建智能体**，传入两个工具和 `checkpointer=InMemorySaver()`。在同一个 `session = {"configurable": {"thread_id": "..."}}` 上运行**两次 `invoke` 调用**；第二个问题必须回指第一个问题而不重复它。用 `reply_text` 打印两次回复。
5. **证明记忆是按线程隔离的**：换一个*新的* `thread_id` 发送同样的追问，打印回复。
6. **流式运行一段两轮对话**：在同一个线程上用 `astream(..., stream_mode="messages")`，只打印 `langgraph_node` 为 `"model"` 的块，并在 `"tools"` 节点运行时打印一个换行。第二轮拒绝第一轮的建议并要求换一个。
7. **以一个反思 markdown 单元收尾**，三到五句话：检查点存储器在轮次之间保存了什么？新的 `thread_id` 为什么回答得不一样？工具内部的状态和检查点存储器的记忆有什么不同？重启内核后它们各自会怎样？

你的 notebook 必须能从上到下无错误地运行。用课程同样的方式检查它，在仓库根目录运行：

```bash
python scripts/validate_notebooks.py --path 02-explore-agentic-frameworks/code_samples/02-assignment-<你的主题>.ipynb
```

### 提交前自查

- notebook 的代码里没有写死任何 API key、模型名或接口地址。
- 查询工具用了 `Annotated`，两个工具都有 docstring。
- 在共享线程上第二次 `invoke` 的回复明显用到了第一轮的信息。
- 新 `thread_id` 上的回复看不出对第一轮的任何记忆。
- 流式输出是逐 token 出现的，而且流式的两轮给出了不同的建议。
- 反思单元回答了全部四个问题。

### 进阶目标（可选）

- 加一个 `list_...` 工具，返回字典的全部键；然后对"这些里面哪些可用？"这个问题，数一数 `result["messages"]` 里的工具调用。
- 第 03 课会教你用 `response_format=` 返回经过校验的 Pydantic 对象而不是散文；在你的查询智能体上试一试。
- 第 04 课会教你用 `HumanInTheLoopMiddleware` 在指定工具运行前暂停智能体。用它给你的带状态工具加一道门。

## 对 AI 智能体框架还有疑问？

在本仓库中提一个 issue，写上课程编号和你尝试过的做法。

## 参考资料

- <a href="https://docs.langchain.com/oss/python/langchain/overview" target="_blank">LangChain 文档</a>
- <a href="https://docs.langchain.com/oss/python/langgraph/overview" target="_blank">LangGraph 文档</a>
- <a href="https://modelcontextprotocol.io/specification" target="_blank">Model Context Protocol 规范</a>

## 上一课

[AI 智能体简介与应用场景](../01-intro-to-ai-agents/README.md)

## 下一课

[理解智能体设计模式](../03-agentic-design-patterns/README.md)
