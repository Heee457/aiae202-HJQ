# Explore AI Agent Frameworks

AI agent frameworks are software platforms designed to simplify the creation, deployment, and management of AI agents. These frameworks provide developers with pre-built components, abstractions, and tools that streamline the development of complex AI systems.

These frameworks help developers focus on the unique aspects of their applications by providing standardized approaches to common challenges in AI agent development. They enhance scalability, accessibility, and efficiency in building AI systems.

## Introduction 

This lesson will cover:

- What are AI Agent Frameworks and what do they enable developers to achieve?
- How can teams use these to quickly prototype, iterate, and improve their agent’s capabilities?
- What does an agent framework give you over the raw SDK?
- How do LangChain, LangGraph and other open-source frameworks compare?
- When should you reach for a graph-based workflow?

## Learning goals

The goals of this lesson are to help you understand:

- The role of AI Agent Frameworks in AI development.
- How to leverage AI Agent Frameworks to build intelligent agents.
- Key capabilities enabled by AI Agent Frameworks.
- The differences between calling a model API directly, using `create_agent`, and building a `StateGraph` workflow.

## What are AI Agent Frameworks and what do they enable developers to do?

Traditional AI Frameworks can help you integrate AI into your apps and make these apps better in the following ways:

- **Personalization**: AI can analyze user behavior and preferences to provide personalized recommendations, content, and experiences.
Example: Streaming services like Netflix use AI to suggest movies and shows based on viewing history, enhancing user engagement and satisfaction.
- **Automation and Efficiency**: AI can automate repetitive tasks, streamline workflows, and improve operational efficiency.
Example: Customer service apps use AI-powered chatbots to handle common inquiries, reducing response times and freeing up human agents for more complex issues.
- **Enhanced User Experience**: AI can improve the overall user experience by providing intelligent features such as voice recognition, natural language processing, and predictive text.
Example: Virtual assistants like Siri and Google Assistant use AI to understand and respond to voice commands, making it easier for users to interact with their devices.

### That all sounds great right, so why do we need the AI Agent Framework?

AI Agent frameworks represent something more than just AI frameworks. They are designed to enable the creation of intelligent agents that can interact with users, other agents, and the environment to achieve specific goals. These agents can exhibit autonomous behavior, make decisions, and adapt to changing conditions. Let's look at some key capabilities enabled by AI Agent Frameworks:

- **Agent Collaboration and Coordination**: Enable the creation of multiple AI agents that can work together, communicate, and coordinate to solve complex tasks.
- **Task Automation and Management**: Provide mechanisms for automating multi-step workflows, task delegation, and dynamic task management among agents.
- **Contextual Understanding and Adaptation**: Equip agents with the ability to understand context, adapt to changing environments, and make decisions based on real-time information.

So in summary, agents allow you to do more, to take automation to the next level, to create more intelligent systems that can adapt and learn from their environment.

## How to quickly prototype, iterate, and improve the agent’s capabilities?

This is a fast-moving landscape, but there are some things that are common across most AI Agent Frameworks that can help you quickly prototype and iterate namely module components, collaborative tools, and real-time learning. Let's dive into these:

- **Use Modular Components**: AI SDKs offer pre-built components such as AI and Memory connectors, function calling using natural language or code plugins, prompt templates, and more.
- **Leverage Collaborative Tools**: Design agents with specific roles and tasks, enabling them to test and refine collaborative workflows.
- **Learn in Real-Time**: Implement feedback loops where agents learn from interactions and adjust their behavior dynamically.

### Use Modular Components

SDKs like LangChain offer pre-built components such as chat model clients, tool definitions, and agent management.

**How teams can use these**: Teams can quickly assemble these components to create a functional prototype without starting from scratch, allowing for rapid experimentation and iteration.

**How it works in practice**: You can use a chat model client to talk to any OpenAI-compatible endpoint, a checkpointer to store and retrieve conversation history, and a system prompt to shape how the agent interacts with users, all without having to build these components from scratch.

**Example code**. Let's look at an example of how you can use LangChain with `ChatOpenAI` to have the model respond to user input with tool calling:

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

What you can see from this example is how the framework extracts key information from user input, such as the destination and date of a flight booking request, and turns it into a call to your `book_flight` function. The tool's docstring and type hints are all the model needs. This modular approach allows you to focus on the high-level logic.

### Leverage Collaborative Tools

Frameworks like LangChain facilitate the creation of multiple agents that can work together.

**How teams can use these**: Teams can design agents with specific roles and tasks, enabling them to test and refine collaborative workflows and improve overall system efficiency.

**How it works in practice**: You can create a team of agents where each agent has a specialized function, such as data retrieval, analysis, or decision-making. These agents can communicate and share information to achieve a common goal, such as answering a user query or completing a task.

**Example code (LangChain)**:

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

What you see in the previous code is how you can create a task that involves multiple agents working together to analyze data. Each agent performs a specific function, and the task is executed by coordinating the agents to achieve the desired outcome. By creating dedicated agents with specialized roles, you can improve task efficiency and performance.

### Learn in Real-Time

Advanced frameworks provide capabilities for real-time context understanding and adaptation.

**How teams can use these**: Teams can implement feedback loops where agents learn from interactions and adjust their behavior dynamically, leading to continuous improvement and refinement of capabilities.

**How it works in practice**: Agents can analyze user feedback, environmental data, and task outcomes to update their knowledge base, adjust decision-making algorithms, and improve performance over time. This iterative learning process enables agents to adapt to changing conditions and user preferences, enhancing overall system effectiveness.

## LangChain and LangGraph

This course uses **LangChain 1.x** for agents and **LangGraph 1.x** for workflows. They are two layers of one stack: `create_agent` is built on LangGraph, so an agent you start with in LangChain can grow into a custom graph without rewriting its tools.

**Use Cases**: Building production-ready AI agents with tool use, multi-turn conversations, structured output, human approval, and explicit multi-step workflows.

Here are the core concepts you will use throughout the course:

- **Chat models**. `ChatOpenAI` speaks the OpenAI Chat Completions protocol, so the same code runs against DeepSeek, OpenAI, a local Ollama server or any other compatible endpoint. The provider is configuration (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`), not code.
- **Tools**. Plain Python functions decorated with `@tool`. The docstring becomes the description the model reads; the type hints become the argument schema.
- **Agents**. `create_agent` combines a chat model, tools and a system prompt into a tool-calling loop: call the model, run the tools it asks for, feed the results back, repeat until the model answers in text.
- **Middleware**. Hooks that run before or after the model or a tool call. The built-in `HumanInTheLoopMiddleware` pauses the agent before a chosen tool runs so a person can approve or reject it (lesson 04 and lesson 06 use it).
- **Checkpointers**. A checkpointer such as `InMemorySaver` saves the conversation after every step, keyed by a `thread_id`. Reuse the id to continue a conversation; use a new id to start fresh.
- **`StateGraph`**. LangGraph's workflow builder: you declare a typed state, nodes (Python functions) and edges (including conditional ones), and compile it into a runnable graph. Lessons 08 and 14 build multi-agent workflows this way.
- **Streaming**. Every agent and graph can be streamed; `stream_mode="messages"` yields model tokens as they arrive.

The three snippets below mirror the notebook for this lesson.

**Create an agent with a tool:**

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

**Remember a conversation with a checkpointer and a thread:**

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

**Stream tokens as they are generated:**

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

## Other Open-Source Agent Frameworks

LangChain is not the only option. The frameworks below solve the same problems with different opinions about how an agent should be orchestrated. All of them are permissively licensed, work with OpenAI-compatible endpoints, and support the Model Context Protocol for tools.

| Framework | Orchestration style | Structured output | Human-in-the-loop | License | Docs |
| --- | --- | --- | --- | --- | --- |
| **LangGraph** (with LangChain) | Graph orchestration: typed state, nodes and edges; `create_agent` for the common tool-calling loop | `response_format=` on the agent, `with_structured_output` on the model | `interrupt()` in any node; `HumanInTheLoopMiddleware` for tool approval | MIT | [docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/overview) |
| **CrewAI** | Role-based crews: agents with roles and goals, tasks, sequential or hierarchical process | `output_pydantic` / `output_json` on a task | `human_input=True` on a task | MIT | [docs.crewai.com](https://docs.crewai.com/) |
| **Pydantic AI** | Typed agents with Pydantic models; Pydantic Graph for explicit state machines | `output_type=` on the agent, validated by Pydantic | Deferred tool calls that require approval before they run | MIT | [ai.pydantic.dev](https://ai.pydantic.dev/) |
| **OpenAI Agents SDK** | Agents, handoffs between agents, guardrails on input and output | `output_type=` on the agent | `needs_approval=True` on a tool; resume from `result.interruptions` | MIT | [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) |
| **smolagents** | Code-acting agents: the model writes Python that calls tools; the default executor runs locally with restrictions, and sandbox isolation requires an explicitly configured executor | No native schema; validate in `final_answer_checks` | Step callbacks and `interrupt()` | Apache-2.0 | [huggingface.co/docs/smolagents](https://huggingface.co/docs/smolagents) |

A few observations to help you read the table:

- **Graph versus roles versus code.** LangGraph asks you to draw the workflow; CrewAI asks you to describe a team; smolagents lets the model write the plan as code. Each is a reasonable default for a different kind of problem.
- **Structured output is table stakes.** Most frameworks can return a validated object instead of free text; they differ mainly in where you declare the schema.
- **Human-in-the-loop needs durable state.** Pausing an agent for approval and resuming it later requires saving state between the two requests. LangGraph's checkpointers make this explicit; the other frameworks handle it at the task or tool level.

## Which Approach Should I Use?

Within the LangChain stack you have three levels to choose from. They are not competitors: `create_agent` compiles to a LangGraph `StateGraph`, and both talk to the model through the same OpenAI-compatible client.

- **Raw OpenAI-compatible SDK** (`openai` package): you build the request, parse tool calls out of the response, run the tools, and loop yourself. Maximum control, no abstractions, and a lot of boilerplate to keep correct.
- **LangChain `create_agent`**: the tool-calling loop, tool schema generation, memory, structured output and middleware are ready-made. One function call gives you a production-ready agent.
- **LangGraph `StateGraph`**: you draw the workflow explicitly as nodes and edges. Use it when the order of steps, branching, parallel work, or long-running approvals need to be visible and testable rather than left to the model.

Still not sure which one to choose?

### Use Cases

Let's see if we can help you by going through some common use cases:

> Q: I'm building an AI agent application and want to get started quickly
>
> A: `create_agent` is a great choice. It provides a simple, Pythonic API that lets you define an agent with tools and instructions in a few lines of code, and it already includes memory, streaming, structured output and human approval.

> Q: I need explicit control over the steps — branching, parallel sub-tasks, retries, or a workflow that pauses for a human and resumes days later
>
> A: A `StateGraph` is the best fit. Every step is a node you can test on its own, edges make the control flow visible, and checkpointers make pausing and resuming a first-class feature.

> Q: I'm still confused, just give me one option
>
> A: Start with `create_agent`. When you outgrow it, remember that it compiles to a LangGraph graph: your tools, model client and checkpointer carry over unchanged into a `StateGraph`, so there is no rewrite.

Let's summarize the key differences in a table:

| Approach | Focus | Core Concepts | Use Cases |
| --- | --- | --- | --- |
| Raw OpenAI-compatible SDK | Direct model calls | Chat completions, tool-call parsing, your own loop | Single calls, experiments, fully custom loops |
| LangChain `create_agent` | Ready-made agent loop | Chat models, tools, system prompt, middleware, checkpointers | Building AI agents, tool use, multi-turn conversations |
| LangGraph `StateGraph` | Explicit workflows | Typed state, nodes, edges, `interrupt()`, checkpointers | Multi-agent systems, branching and parallel workflows, long-running approvals |

## Sample Codes

- Python: [LangChain agent](./code_samples/02-python-langchain-agent.ipynb)

## Assignment: An Agent That Remembers the Conversation

The notebook for this lesson adds two things to the agent from lesson 01: a **checkpointer** (`InMemorySaver`) keyed by a `thread_id`, so the agent remembers earlier turns, and a tool with state of its own, so two calls in a row never return the same answer. Build a multi-turn agent in a **different domain** that shows both. Some ideas: a recipe picker, a gym class scheduler, a library helper, a board-game night planner, a language tutor.

### Requirements

1. **Create a new notebook** in `code_samples/`, named `02-assignment-<your-topic>.ipynb`. Start it with the same setup cell as the lesson notebook, reading `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` from `.env`. Never paste an API key into the notebook.
2. **Define a lookup tool** with `@tool` whose parameter is described with `Annotated[str, "..."]`, like `check_destination_availability`, backed by a dictionary of at least five entries.
3. **Define a stateful tool** with no arguments that remembers its last result in a module-level variable (the `_last_destination` pattern with `global`), so two calls in a row never match.
4. **Create the agent** with `create_agent`, both tools and `checkpointer=InMemorySaver()`. Run **two `invoke` calls** on one `session = {"configurable": {"thread_id": "..."}}`; the second question must refer back to the first without repeating it. Print both replies with `reply_text`.
5. **Prove the memory is per thread**: send the same follow-up on a *new* `thread_id` and print the reply.
6. **Stream a two-turn conversation** on one thread with `astream(..., stream_mode="messages")`, printing only chunks whose `langgraph_node` is `"model"` and a newline when the `"tools"` node runs. The second turn rejects the first suggestion and asks for another.
7. **Finish with a reflection** markdown cell of three to five sentences: what does the checkpointer store between turns, why did the new `thread_id` answer differently, how does the state inside your tool differ from the checkpointer's memory, and what happens to each when you restart the kernel?

Your notebook must run top to bottom without errors. Check it the same way the course does, from the repository root:

```bash
python scripts/validate_notebooks.py --path 02-explore-agentic-frameworks/code_samples/02-assignment-<your-topic>.ipynb
```

### Self-check before you hand it in

- The notebook has no API key, model name or base URL typed into the code.
- The lookup tool uses `Annotated` and both tools have a docstring.
- The second `invoke` on the shared thread clearly uses information from the first turn.
- The reply on the new `thread_id` shows no memory of the first turn.
- The streamed output appears token by token, and the two streamed turns suggest different things.
- The reflection cell answers all four questions.

### Stretch goals (optional)

- Add a `list_...` tool that returns every key of your dictionary and count the tool calls in `result["messages"]` for "which of these are available?".
- Lesson 03 shows how `response_format=` returns a validated Pydantic object instead of prose; try it on your lookup agent.
- Lesson 04 shows how `HumanInTheLoopMiddleware` pauses the agent before a chosen tool runs. Gate your stateful tool with it.

## Got More Questions about AI Agent Frameworks?

Open an issue in this repository with the lesson number and what you tried.

## References

- <a href="https://docs.langchain.com/oss/python/langchain/overview" target="_blank">LangChain documentation</a>
- <a href="https://docs.langchain.com/oss/python/langgraph/overview" target="_blank">LangGraph documentation</a>
- <a href="https://modelcontextprotocol.io/specification" target="_blank">Model Context Protocol specification</a>

## Previous Lesson

[Introduction to AI Agents and Agent Use Cases](../01-intro-to-ai-agents/README.md)

## Next Lesson

[Understanding Agentic Design Patterns](../03-agentic-design-patterns/README.md)
