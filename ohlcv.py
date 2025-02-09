import requests
import json
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

load_dotenv()

url = "https://streaming.bitquery.io/graphql"
BITQURERY_TOKEN = os.getenv("BITQURERY_TOKEN")
WETH = "0x4200000000000000000000000000000000000006"


@dataclass
class Trade:
    high: float
    low: float
    open: float
    close: float


@dataclass
class Block:
    testfield: datetime


@dataclass
class DEXTrade:
    Block: Block
    Trade: Trade
    count: str
    volume: str


@dataclass
class EVMData:
    DEXTradeByTokens: List[DEXTrade]


@dataclass
class EVM:
    DEXTradeByTokens: List[DEXTrade]


@dataclass
class OHLCVResponse:
    data: EVM


def get_ohlcv(
    base_token: str,
    quote_token: str = WETH,
    limit: int = 100,
    since: Optional[datetime] = None,
) -> OHLCVResponse:
    # Build the "where" clause conditions
    where_conditions = [
        (
            "Trade: {"
            "Currency: {"
            'SmartContract: { is: "' + base_token + '" }'
            "} "
            "Side: {"
            "Currency: {"
            'SmartContract: { is: "' + quote_token + '" }'
            "} "
            "Type: { is: buy }"
            "} "
            "PriceAsymmetry: { lt: 0.1 }"
            "}"
        )
    ]
    if since is not None:
        # Ensure the timestamp is in ISO format (the Bitquery API expects ISO8601)
        since_str = since.isoformat()
        where_conditions.append('Block: { testfield: { gt: "' + since_str + '" } }')
    where_clause = ", ".join(where_conditions)

    query = f"""
    {{
      EVM(network: base, dataset: archive) {{
        DEXTradeByTokens(
          orderBy: {{ descendingByField: "Block_testfield" }}
          where: {{ {where_clause} }}
          limit: {{ count: {limit} }}
        ) {{
          Block {{
            testfield: Time(interval: {{ in: minutes, count: 5 }})
          }}
          volume: sum(of: Trade_Amount)
          Trade {{
            high: Price(maximum: Trade_Price)
            low: Price(minimum: Trade_Price)
            open: Price(minimum: Block_Number)
            close: Price(maximum: Block_Number)
          }}
          count
        }}
      }}
    }}
    """

    payload = json.dumps({"query": query, "variables": "{}"})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BITQURERY_TOKEN}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
        raise Exception(f"Failed to get OHLCV: {response.status_code}, {response.text}")

    json_data = response.json()

    # Convert the JSON response to our dataclass structure
    return OHLCVResponse(
        data=EVM(
            DEXTradeByTokens=[
                DEXTrade(
                    Block=Block(
                        testfield=datetime.fromisoformat(
                            item["Block"]["testfield"].replace("Z", "+00:00")
                        )
                    ),
                    Trade=Trade(
                        high=float(item["Trade"]["high"]),
                        low=float(item["Trade"]["low"]),
                        open=float(item["Trade"]["open"]),
                        close=float(item["Trade"]["close"]),
                    ),
                    count=item["count"],
                    volume=item["volume"],
                )
                for item in json_data["data"]["EVM"]["DEXTradeByTokens"]
            ]
        )
    )


def draw_ohlcv(result: OHLCVResponse):
    data = {
        "Date": [trade.Block.testfield for trade in result.data.DEXTradeByTokens],
        "Open": [trade.Trade.open for trade in result.data.DEXTradeByTokens],
        "High": [trade.Trade.high for trade in result.data.DEXTradeByTokens],
        "Low": [trade.Trade.low for trade in result.data.DEXTradeByTokens],
        "Close": [trade.Trade.close for trade in result.data.DEXTradeByTokens],
        "Volume": [float(trade.volume) for trade in result.data.DEXTradeByTokens],
    }

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)  # Sort by date

    # Create the OHLCV chart
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]}
    )

    # Plot candlesticks
    ap = mpf.make_addplot(df[["Open", "High", "Low", "Close"]], type="candle", ax=ax1)
    mpf.plot(df, type="candle", style="charles", addplot=ap, ax=ax1, volume=False)
    ax1.set_title("OHLCV Chart")

    # Plot volume bars
    ax2.bar(df.index, df["Volume"], color="gray", alpha=0.5)
    ax2.set_ylabel("Volume")

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Show the plot
    plt.show()


if __name__ == "__main__":
    # Example usage
    base_token = "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825"
    result = get_ohlcv(base_token)
    draw_ohlcv(result)
