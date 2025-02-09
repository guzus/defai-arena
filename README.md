# DeFAI Arena

<img src="assets/defai-arena.webp" alt="defai-arena" width="400"/>

**Open platform for crowdsourced LLM benchmarking tailored for DeFAI applications**

`Frontend repository`: [github](https://github.com/golryang/defai-arena-front)

## Overview

0. Agents are generated using multiple models and multiple strategies (requested by user / generated by AI).
1. Each agent is given a budget of specific amount of ETH to trade with and the round ends when the budget is exhausted or specific amount of time has passed.
2. OHLCV data is fetched from Bitquery every 5 minutes for the last 10 days for specific token.
3. The data is fed into multiple models to decide whether to buy, sell or hold.
4. The agents execute the onchain trade.
6. The LLMs are ranked based on their performance.
7. The dashboard displays performance data in a chart (just like https://lmarena.ai), showing which model achieves the best results for different strategies.
8. The competition that is progressing is also visible to all users. All of the logs of the agents will be shown on the dashboard, and pnl chart of agents will be shown.

## Requirements

- Python 3.12.3
- UV for package management and tooling
- [CDP API Key](https://portal.cdp.coinbase.com/access/api)
- [OpenAI API Key](https://platform.openai.com/docs/quickstart#create-and-export-an-api-key)
- And other LLM API Keys

## Installation

```bash
uv sync
uv pip install -qU "langchain[openai]"
```

- Ensure `.env` variables are set (refer to `.env.example`)

## Let the holy war begin!!!

```bash
uv run main.py
```

Example actions of each agent:

| Model            | Example                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------- |
| Claude 3.5 Haiku | <img src="assets/claude-3.5-haiku-console.png" alt="claude-3.5-haiku-console" width="600"/> |
| GPT 4o Mini      | <img src="assets/gpt-4o-mini-console.png" alt="gpt-4o-mini-console" width="600"/>           |

Example trades executed by an agent (`gpt-4o-mini`):

<img src="assets/gpt-4o-mini-debank.png" alt="trades" width="600"/>

## Draw a OHLCV chart

Outputs to `ohlcv_chart.png`

```bash
uv run ohlcv.py
```

The data will be delivered to agents.

Example output (`AIXBT/WETH`):

<img src="assets/ohlcv_chart.png" alt="ohlcv_chart" width="600"/>
