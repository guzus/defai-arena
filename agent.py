import json
import os
from dotenv import load_dotenv

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Import CDP Agentkit Langchain Extension.
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper


load_dotenv()

def initialize_agent(llm, thread_id):
    """Initialize the agent with CDP Agentkit."""
    wallet_data = None 
    wallet_data_file = f"wallet_data_{thread_id}.txt"

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file, "r") as f:
            wallet_data = f.read()
        # print(f"[{thread_id}]: {wallet_data}")
    else:
        print(f"[{thread_id}]: load failed.")

    # Configure CDP Agentkit Langchain Extension.
    values = {}
    if wallet_data is not None:
        # If there is a persisted agentic wallet, load it and pass to the CDP Agentkit Wrapper.
        values = {"cdp_wallet_data": wallet_data}

    agentkit = CdpAgentkitWrapper(**values)

    # persist the agent's CDP MPC Wallet Data.
    wallet_data = agentkit.export_wallet()
    export_wallet_data = wallet_data
    wallet_data_file = f"wallet_data_{thread_id}.txt"

    with open(wallet_data_file, "w") as f:
        f.write(export_wallet_data)

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()
    # Store buffered conversation history in memory.
    memory = MemorySaver()
    config = {"configurable": {"thread_id": thread_id}}

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=(
            "You are a helpful agent that can interact onchain using the Coinbase Developer Platform AgentKit. "
            "You are empowered to interact onchain using your tools. If you ever need funds, you can request "
            "them from the faucet if you are on network ID 'base-sepolia'. If not, you can provide your wallet "
            "details and request funds from the user. Before executing your first action, get the wallet details"
        ),
    ), config
