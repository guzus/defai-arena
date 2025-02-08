import time
import threading

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage

from chatbot import initialize_agent

# Dummy function to get latest candle data.
def fetch_candle_data(symbol):
    # Replace with your API call / data fetching logic.
    curr_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # Example candle: you can extend this with real data fields.
    candle_data = (
        f"Timestamp: {curr_time}; Open: 100; High: 110; "
        f"Low: 95; Close: 105; Volume: 1500"
    )
    return candle_data

# Trading loop for each LLM model.
def run_trading_mode(agent_executor, config, model_name, interval=300):
    print(f"Starting trading mode for {model_name}...")
    # Simulated portfolio for demonstration.
    portfolio = {"cash": 10000, "position": 0}
    
    while True:
        candle = fetch_candle_data()
        prompt = (
            "You are an autonomous trading agent that makes trading decisions every 15 minutes based on candlestick data. "
            "Below is the latest market data:\n\n"
            f"{candle}\n\n"
            "Based on the above data, please decide whether to BUY, HOLD, or SELL. "
            "Provide a short rationale with your decision."
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

        # Here, update your simulated portfolio based on the decision.
        # For example, a simple simulation might be:
        # if "BUY" in decision.upper():
        #     portfolio["position"] = portfolio["cash"] / current_price
        #     portfolio["cash"] = 0
        # elif "SELL" in decision.upper():
        #     portfolio["cash"] = portfolio["position"] * current_price
        #     portfolio["position"] = 0
        # (current_price can be extracted from candle data e.g. CDP "Close" price)

        print(f"[{model_name}] current simulated portfolio: {portfolio}")
        print("--------------------------------------------------")
        
        time.sleep(interval)

def main():
    symbol = input("Enter the trading symbol (e.g., BTC-USD): ").strip()

    llms = ["OpenAI", "DeepSeek"]

    models = {
        "OpenAI": ["gpt-4o-mini"],
        "DeepSeek": ["deepseek-chat"]
    }

    # Create a list to store trading threads.
    trading_threads = []

    # For each LLM type and model, create and start a trading thread.
    for llm_name in llms: 
        for model in models.get(llm_name, []):
            if llm_name == "OpenAI":
                llm_instance = initialize_agent(ChatOpenAI(model=model))
            elif llm_name == "DeepSeek":
                llm_instance = initialize_agent(ChatDeepSeek(model=model))
            
            # Start a separate thread for each trading agent.
            thread = threading.Thread(
                target=run_trading_mode,
                args=(llm_instance, {"configurable": {"thread_id": f"{llm_name}-{model} Trading"}}, f"{llm_name}-{model}"),
                daemon=True
            )
            trading_threads.append(thread)
            thread.start()

    # Keep the main thread alive so trading threads can run.
    try:
        while True:
            time.sleep(300)
    except KeyboardInterrupt:
        print("Exiting trading application.")

if __name__ == "__main__":
    main()
