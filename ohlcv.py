import requests
import json
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List
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


def get_ohlcv(base_token: str, quote_token: str = WETH) -> OHLCVResponse:
    query = """
    {
      EVM(network: base, dataset: archive) {
        DEXTradeByTokens(
          orderBy: {descendingByField: "Block_testfield"}
          where: {
            Trade: {
              Currency: {
                SmartContract: {is: "%s"}
              }
              Side: {
                Currency: {
                  SmartContract: {is: "%s"}
                }
                Type: {is: buy}
              }
              PriceAsymmetry: {lt: 0.1}
            }
          }
          limit: {count: 100}
        ) {
          Block {
            testfield: Time(interval: {in: minutes, count: 5})
          }
          volume: sum(of: Trade_Amount)
          Trade {
            high: Price(maximum: Trade_Price)
            low: Price(minimum: Trade_Price)
            open: Price(minimum: Block_Number)
            close: Price(maximum: Block_Number)
          }
          count
        }
      }
    }
    """ % (
        base_token,
        quote_token,
    )

    payload = json.dumps({"query": query, "variables": "{}"})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BITQURERY_TOKEN}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
        raise Exception(f"Failed to get OHLCV: {response.status_code}")

    json_data = response.json()

    # Convert the JSON response to dataclass
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

    # Plot candlesticks - use addplot instead of plot
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
    base_token = "0x52b492a33E447Cdb854c7FC19F1e57E8BfA1777D"
    result = get_ohlcv(base_token)
    draw_ohlcv(result)
