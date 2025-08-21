# Crypto Arbitrage Monitor

This script is a command-line tool designed to monitor cryptocurrency prices across multiple exchanges and identify arbitrage opportunities in real-time. It fetches order book data, calculates potential spreads, and displays profitable trades based on user-defined parameters.

## Features

- **Multi-Exchange Support:** Monitors a wide range of popular cryptocurrency exchanges.
- **Real-Time Data:** Fetches live ticker and order book data to ensure accuracy.
- **Configurable Parameters:** Allows users to set the desired arbitrage percentage, minimum liquidity, and trade volume.
- **Concurrent Processing:** Utilizes parallel processing to efficiently gather data from multiple exchanges and pairs.
- **Liquidity Analysis:** Considers the available liquidity to ensure that identified opportunities are viable.
- **Blacklist Functionality:** Allows users to exclude specific trading pairs from the analysis.
- **Currency Conversion:** Automatically converts prices from BRL and USD to USDT for standardized comparison.

## How It Works

The script performs the following steps:

1.  **Initializes Exchanges:** Sets up the specified exchanges for buying and selling using the `ccxt` library.
2.  **Loads Trading Pairs:** Reads the trading pairs for each exchange from the corresponding `.pairs` files in the `pairs/` directory.
3.  **Fetches Prices and Liquidity:** Concurrently fetches the latest prices and liquidity information for all trading pairs.
4.  **Identifies Opportunities:** Compares the prices between the buying and selling exchanges to find potential arbitrage opportunities that meet the defined criteria (e.g., spread percentage, liquidity).
5.  **Calculates Average Spread:** For each opportunity, it analyzes the order book to calculate the average spread based on a specified trade volume, providing a more realistic profit estimate.
6.  **Displays Results:** Prints the identified arbitrage opportunities, including the trading pair, exchanges, spread, and order book details.

## Configuration

Before running the script, you need to configure the following parameters in `arbitrage_monitor.py`:

-   `exchanges_compra_names`: A list of exchanges to be used for buying.
-   `exchanges_venda_names`: A list of exchanges to be used for selling.
-   `percentual_arbitragem`: The minimum spread percentage to be considered an opportunity.
-   `percentual_max_arbitragem`: The maximum spread percentage to avoid unrealistic opportunities.
-   `liquidez_minima`: The minimum required liquidity in USDT for a trade to be considered.
-   `numero_ordens`: The number of orders to fetch from the order book.
-   `volume_arbitragem_usdt`: The trade volume in USDT to be used for calculating the average spread.

You also need to configure the trading pairs for each exchange by editing the files in the `pairs/` directory. Each file should contain a list of trading pairs in the format `'COIN/QUOTE'`.

## Dependencies

The script requires the following Python library:

-   `ccxt`: A library for cryptocurrency trading and exchange integration.

You can install it using pip:

```bash
pip install ccxt
```

## How to Run

To run the script, simply execute the following command in your terminal:

```bash
python arbitrage_monitor.py
```

The script will start monitoring the exchanges and print any arbitrage opportunities it finds.
