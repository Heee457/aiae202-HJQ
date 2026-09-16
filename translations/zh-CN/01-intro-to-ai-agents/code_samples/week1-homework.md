# 第 1 周作业

个人主题的智能体作业为01-assignment-stock-recommender.ipynb文件。

## 一、演示观察三条

1. **完全没看懂的一步（智能体当时在干什么？）：**

    `agent.invoke()` 内部如何自动完成工具调用？代码里没有单独写一行 `get_destinations()`，框架却能根据模型用户提问执行这个函数，再把结果交回模型组织答案。

2. **觉得可疑的一步（为什么可疑？）：**

   `get_destinations` 只返回城市名称，最终回答却补充了气候、海滩等信息，模型自动补全了选择目的地的理由，但这些内容没有直接得到该次工具返回的支持。

3. **最想问的一个问题：**

   仅在系统提示词中要求“不编造”，智能体回答时就一定不会编造吗？有什么办法可以验证或者保证这个事情？

## 二、接口检查输出（原样粘贴）

```text
$ python scripts/check_endpoint.py

Endpoint: https://api.deepseek.com/v1
Model:    deepseek-v4-pro

capability  result    used by lessons
chat        PASS      all lessons
tools       PASS      01, 03-05, 07-13, 16-18 (create_agent needs tool calling)
structured  PASS      03, 07, 08 (structured output forces a tool call; DeepSeek thinking models need LLM_EXTRA_BODY to disable thinking)
vision      PASS      10 (expense demo), 15 (browser-use) — optional, set VISION_* to enable

Ready: this endpoint supports everything the course requires.
```

## 三、危险工具判断

我认为 `query_orders(sql)` 最危险，因为它把任意 SQL 的执行能力交给模型，若数据库权限没有限制，就可能误改、删除数据或读取其他客户的订单；应改为只接收订单号等结构化参数，由程序校验订单归属后执行固定的参数化查询，并使用只读账号、限制返回范围。

`send_confirmation(to, body)` 风险在于若邮件存在问题发送，如错误收件人或错误正文，邮件通常不能撤回。应先生成草稿，展示收件人和正文，经用户明确确认后再发送。

`get_weather(city)` 无风险，但仍需要校验城市是否存在、数据接口是否可用，获取的数据时间是否和提问时间一致？
