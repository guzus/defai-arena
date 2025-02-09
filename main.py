import time
import threading

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from langchain_core.messages import HumanMessage

from agent import initialize_agent
from ohlcv import get_ohlcv, OHLCVResponse, EVM
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Global cache for OHLCV data
ohlcv_cache = {}
ohlcv_cache_lock = threading.Lock()


def update_ohlcv_cache(token: str, interval=5 * 60, limit: int = 100):
    # Track the latest fetched timestamp per token
    last_timestamp = None
    while True:
        try:
            # Only fetch new data if we have a last timestamp
            data = (
                get_ohlcv(token, limit=limit, since=last_timestamp)
                if last_timestamp
                else get_ohlcv(token, limit=limit)
            )
            if data.data.DEXTradeByTokens:
                # Assume that the API orders trades descending, so the first one is the latest trade.
                latest_trade_time = data.data.DEXTradeByTokens[0].Block.testfield
                last_timestamp = latest_trade_time

                with ohlcv_cache_lock:
                    # Merge new data into the cache if it exists. Here we deduplicate based on the timestamp.
                    if token in ohlcv_cache:
                        old_trades = ohlcv_cache[token].data.DEXTradeByTokens
                        # Build a dict using timestamp as key for deduplication
                        trades_dict = {
                            trade.Block.testfield: trade for trade in old_trades
                        }
                        for trade in data.data.DEXTradeByTokens:
                            trades_dict[trade.Block.testfield] = trade
                        merged_trades = sorted(
                            trades_dict.values(), key=lambda t: t.Block.testfield
                        )
                        ohlcv_cache[token] = OHLCVResponse(
                            data=EVM(DEXTradeByTokens=merged_trades)
                        )
                    else:
                        ohlcv_cache[token] = data
        except Exception as e:
            logging.error(f"Error updating OHLCV cache: {e}")
        time.sleep(interval)


def get_ohlcv_cached(token: str):
    """Get OHLCV data from cache"""
    with ohlcv_cache_lock:
        return ohlcv_cache.get(token)


# Trading loop for each LLM model.
def run_trading_mode(agent_executor, config, model_name, token, interval=5 * 60):

    while True:
        result = get_ohlcv_cached(token)
        candle = result

        prompt = (
            "You are an autonomous trading agent that makes trading decisions every 5 minutes based on candlestick data. "
            "Below is the latest market data:\n\n"
            f"token: {token}\n\n"
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
