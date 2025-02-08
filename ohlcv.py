import requests
import json
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List
from datetime import datetime

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
          limit: {count: 10}
        ) {
          Block {
            testfield: Time(interval: {in: hours, count: 1})
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


if __name__ == "__main__":
    # Example usage
    base_token = "0x52b492a33E447Cdb854c7FC19F1e57E8BfA1777D"
    result = get_ohlcv(base_token)

    for trade in result.data.DEXTradeByTokens:
        print(f"Time: {trade.Block.testfield}")
        print(f"High: {trade.Trade.high}")
        print(f"Low: {trade.Trade.low}")
        print(f"Volume: {trade.volume}")
        print("---")
