import time
import threading

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from langchain_core.messages import HumanMessage

from agent import initialize_agent
from ohlcv import get_ohlcv


def fetch_candle_data(token: str):
    return get_ohlcv(token)


# Trading loop for each LLM model.
def run_trading_mode(agent_executor, config, model_name, token, interval=300):

    while True:
        result = get_ohlcv(token)
        candle = result

        prompt = (
            "You are an autonomous trading agent that makes trading decisions every 15 minutes based on candlestick data. "
            "Below is the latest market data:\n\n"
            f"{candle}\n\n"
            "Based on the above data, please decide whether to BUY, HOLD, or SELL. "
            "Provide a short rationale with your decision, and execute the trade if necessary."
            "The size of trade is 0.001 ETH."
        )

        # For this example, we assume a streaming interface
        # You might also use a non-streaming API call if available.
        decisions = []
        for chunk in agent_executor.stream(
            {"messages": [HumanMessage(content=prompt)]}, config
        ):
            if "agent" in chunk and chunk["agent"]["messages"]:
                decision = chunk["agent"]["messages"][0].content
                decisions.append(decision)
                print(f"[{model_name}] decision: {decision}")

        # print(f"[{model_name}] current simulated portfolio: {portfolio}")
        print("--------------------------------------------------")

        time.sleep(interval)


def main():
    llms = ["OpenAI", "Anthropic"]

    models = {"OpenAI": ["gpt-4o-mini"], "Anthropic": ["claude-3-5-haiku-latest"]}

    token = "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825"  # AIXBT

    # Create a list to store trading threads.
    trading_threads = []

    # For each LLM type and model, create and start a trading thread.
    for llm_name in llms:
        for model in models.get(llm_name, []):
            if llm_name == "OpenAI":
                llm_instance, conf = initialize_agent(
                    ChatOpenAI(model=model), thread_id=f"{llm_name}-{model}-Trading"
                )
            elif llm_name == "Anthropic":
                llm_instance, conf = initialize_agent(
                    ChatAnthropic(model=model), thread_id=f"{llm_name}-{model}-Trading"
                )

            # Start a separate thread for each trading agent.
            thread = threading.Thread(
                target=run_trading_mode,
                args=(
                    llm_instance,
                    {"configurable": {"thread_id": f"{llm_name}-{model}-Trading"}},
                    f"{llm_name}-{model}",
                    token,
                ),
                daemon=True,
            )
            trading_threads.append(thread)
            thread.start()

    # Keep the main thread alive so trading threads can run.
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting trading application.")


if __name__ == "__main__":
    main()
