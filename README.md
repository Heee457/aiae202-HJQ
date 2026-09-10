# AIAE202 · Agentic AI 开发实践 — 课程仓库

这是 AIAE202 的学生仓库模板。点右上角 **Fork** 得到属于你自己的一份，接下来的练习和作业都放在这里。

课程内容取自开源课程 [AI Agents for Beginners](https://github.com/liubarnabas/ai-agents-for-beginners)。本仓库先放前三课，后续课程会随进度陆续加入；每课有英文原版和中文翻译。

| 课程 | 英文 | 中文 |
|---|---|---|
| 00 课程环境准备 | [00-course-setup](./00-course-setup/README.md) | [zh-CN](./translations/zh-CN/00-course-setup/README.md) |
| 01 AI 智能体入门 | [01-intro-to-ai-agents](./01-intro-to-ai-agents/README.md) | [zh-CN](./translations/zh-CN/01-intro-to-ai-agents/README.md) |
| 02 探索智能体框架 | [02-explore-agentic-frameworks](./02-explore-agentic-frameworks/README.md) | [zh-CN](./translations/zh-CN/02-explore-agentic-frameworks/README.md) |

## 三步跑起来

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                  # 填入 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
python scripts/check_endpoint.py                      # chat 和 tools 必须 PASS
```

然后打开 `01-intro-to-ai-agents/code_samples/01-python-langchain-agent.ipynb`，从上到下运行。详细说明见[课程环境准备](./translations/zh-CN/00-course-setup/README.md)。

## 作业放哪里

每课 README 末尾有一节"作业"。作业 notebook 放在该课的 `code_samples/` 目录下，命名为 `<NN>-assignment-<你的主题>.ipynb`；每周的运行解读放在同一目录的 `week<N>-homework.md`。提交前用课程同样的方式检查：

```bash
python scripts/validate_notebooks.py --path 01-intro-to-ai-agents/code_samples/01-assignment-<你的主题>.ipynb
```

`.env` 已在 `.gitignore` 里，API key 只留在本机。**不要把 key 写进任何 notebook。**

---

## English

This is the student repository template for AIAE202 (Agentic AI Development in Practice). Fork it; your exercises and assignments live here.

The lessons come from the open-source course [AI Agents for Beginners](https://github.com/liubarnabas/ai-agents-for-beginners). This repository starts with lessons 00 to 02 and grows as the course proceeds. Each lesson has the English original and a Simplified Chinese translation.

Setup: create a Python 3.12 virtual environment, `pip install -r requirements.txt`, copy `.env.example` to `.env` and fill in `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`, then run `python scripts/check_endpoint.py`. See [Course Setup](./00-course-setup/README.md).

Assignments: every lesson README ends with an assignment. Put the notebook in that lesson's `code_samples/` as `<NN>-assignment-<your-topic>.ipynb` and check it with `python scripts/validate_notebooks.py --path <notebook>`. Never commit an API key.
