import time
import threading

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from langchain_core.messages import HumanMessage

from agent import initialize_agent
from ohlcv import get_ohlcv_cached, compress_ohlcv_data, update_ohlcv_cache
import logging

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Create file handler
file_handler = logging.FileHandler("app.log", mode="a")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Add both handlers to the logger
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# Suppress httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)


# Trading loop for each LLM model.
def run_trading_mode(agent_executor, config, model_name, token, interval=5 * 60):

    while True:
        candle = get_ohlcv_cached(token)
        compressed_candle = compress_ohlcv_data(candle)
        prompt = (
            "You are an autonomous trading agent that makes trading decisions every 5 minutes based on candlestick data. "
            "Below is the latest market data:\n\n"
            f"token: {token}\n\n"
            f"{compressed_candle}\n\n"
            "Based on the above data, please decide whether to BUY, HOLD, or SELL. "
            "Provide a short rationale with your decision, and execute the trade if necessary."
            "The size of trade is 0.001 ETH worth of a token."
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
                logging.info(f"[{model_name}] decision: {decision}")

        # print(f"[{model_name}] current simulated portfolio: {portfolio}")
        logging.info("--------------------------------------------------")

        time.sleep(interval)


def main():
    llms = ["OpenAI", "Anthropic"]

    models = {"OpenAI": ["gpt-4o-mini"], "Anthropic": ["claude-3-5-haiku-latest"]}

    token = "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825"  # AIXBT

    logging.info(f"Starting trading for token: {token}")

    # Start OHLCV cache update thread
    ohlcv_thread = threading.Thread(
        target=update_ohlcv_cache, args=(token,), daemon=True
    )
    ohlcv_thread.start()

    time.sleep(5)

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
        logging.info("Exiting trading application.")


if __name__ == "__main__":
    main()
