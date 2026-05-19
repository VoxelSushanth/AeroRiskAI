#!/usr/bin/env python3
"""
Generate synthetic trading data for testing and benchmarking.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any


def generate_order(
    user_id: str,
    symbol: str,
    base_price: float
) -> Dict[str, Any]:
    """Generate a synthetic order."""
    side = random.choice(['BUY', 'SELL'])
    quantity = round(random.uniform(1, 1000), 2)
    
    # Price varies slightly from base
    price_variation = random.uniform(-0.02, 0.02)
    price = round(base_price * (1 + price_variation), 2)
    
    order_types = ['LIMIT', 'MARKET', 'STOP_LIMIT']
    order_type = random.choices(
        order_types, 
        weights=[0.7, 0.2, 0.1]
    )[0]
    
    return {
        "order_id": f"ORD-{uuid.uuid4().hex[:12].upper()}",
        "user_id": user_id,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price if order_type != 'MARKET' else None,
        "order_type": order_type,
        "time_in_force": random.choice(['GTC', 'DAY', 'IOC']),
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "metadata": {
            "client_order_id": f"CLI-{uuid.uuid4().hex[:8]}",
            "source": random.choice(['WEB', 'API', 'MOBILE', 'ALGO']),
            "ip_address": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        }
    }


def generate_trade(
    order: Dict[str, Any],
    match_price: float,
    match_quantity: float
) -> Dict[str, Any]:
    """Generate a trade from matched order."""
    return {
        "trade_id": f"TRD-{uuid.uuid4().hex[:12].upper()}",
        "order_id": order["order_id"],
        "symbol": order["symbol"],
        "side": order["side"],
        "price": match_price,
        "quantity": match_quantity,
        "value_usd": round(match_price * match_quantity, 2),
        "fee_usd": round(match_price * match_quantity * 0.001, 2),
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "counterparty_order_id": f"ORD-{uuid.uuid4().hex[:12].upper()}",
        "liquidity": random.choice(['MAKER', 'TAKER'])
    }


def generate_anomalous_orders(
    user_id: str,
    symbol: str,
    base_price: float,
    anomaly_type: str
) -> List[Dict[str, Any]]:
    """Generate orders with anomalous patterns for testing."""
    orders = []
    
    if anomaly_type == "wash_trading":
        # Rapid buy/sell at similar prices
        for i in range(10):
            side = 'BUY' if i % 2 == 0 else 'SELL'
            orders.append(generate_order(user_id, symbol, base_price))
            orders[-1]["side"] = side
            orders[-1]["quantity"] = 100.0
            
    elif anomaly_type == "spoofing":
        # Large orders that would be cancelled
        for i in range(5):
            order = generate_order(user_id, symbol, base_price)
            order["quantity"] = random.uniform(5000, 10000)
            order["price"] = base_price * (1 + 0.05 * (-1 if i % 2 == 0 else 1))
            order["metadata"]["spoof_risk"] = True
            orders.append(order)
            
    elif anomaly_type == "velocity":
        # Very high order frequency
        for i in range(50):
            orders.append(generate_order(user_id, symbol, base_price))
            
    elif anomaly_type == "vwap_deviation":
        # Orders significantly away from market
        for i in range(5):
            order = generate_order(user_id, symbol, base_price)
            order["price"] = base_price * random.choice([0.8, 0.85, 1.15, 1.2])
            orders.append(order)
    
    return orders


def generate_synthetic_dataset(
    num_users: int = 100,
    num_symbols: int = 20,
    num_orders_per_user: int = 50,
    anomaly_percentage: float = 0.05
) -> Dict[str, Any]:
    """Generate complete synthetic dataset."""
    
    # Define symbols with base prices
    symbols = {
        "AAPL": 175.50,
        "GOOGL": 140.25,
        "MSFT": 380.00,
        "AMZN": 178.50,
        "META": 485.00,
        "TSLA": 245.00,
        "NVDA": 875.00,
        "JPM": 195.00,
        "V": 280.00,
        "JNJ": 155.00,
        "WMT": 165.00,
        "PG": 158.00,
        "MA": 450.00,
        "HD": 345.00,
        "DIS": 110.00,
        "NFLX": 625.00,
        "PYPL": 62.00,
        "INTC": 32.00,
        "AMD": 165.00,
        "CRM": 275.00
    }
    
    # Generate users
    users = [f"USR-{str(i).zfill(3)}" for i in range(1, num_users + 1)]
    
    # Generate orders
    all_orders = []
    all_trades = []
    anomaly_count = 0
    
    target_anomalies = int(num_users * num_orders_per_user * anomaly_percentage)
    
    for user_id in users:
        for _ in range(num_orders_per_user):
            symbol = random.choice(list(symbols.keys()))
            base_price = symbols[symbol]
            
            # Decide if this should be anomalous
            if anomaly_count < target_anomalies and random.random() < 0.1:
                anomaly_type = random.choice([
                    "wash_trading", "spoofing", "velocity", "vwap_deviation"
                ])
                anomalous_orders = generate_anomalous_orders(
                    user_id, symbol, base_price, anomaly_type
                )
                all_orders.extend(anomalous_orders)
                anomaly_count += len(anomalous_orders)
            else:
                order = generate_order(user_id, symbol, base_price)
                all_orders.append(order)
            
            # Simulate some trades
            if random.random() < 0.7:  # 70% fill rate
                order = all_orders[-1]
                trade = generate_trade(
                    order,
                    order["price"] or base_price,
                    min(order["quantity"], random.uniform(10, 100))
                )
                all_trades.append(trade)
    
    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + 'Z',
            "num_users": num_users,
            "num_symbols": len(symbols),
            "num_orders": len(all_orders),
            "num_trades": len(all_trades),
            "num_anomalies": anomaly_count
        },
        "symbols": symbols,
        "users": users,
        "orders": all_orders,
        "trades": all_trades
    }


def main():
    """Generate and save synthetic data."""
    print("Generating synthetic trading dataset...")
    
    dataset = generate_synthetic_dataset(
        num_users=100,
        num_symbols=20,
        num_orders_per_user=50,
        anomaly_percentage=0.05
    )
    
    # Save to file
    output_file = "/workspace/data/seed/synthetic_trading_data.json"
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\n✅ Synthetic dataset generated successfully!")
    print(f"   Output file: {output_file}")
    print(f"   Users: {dataset['metadata']['num_users']}")
    print(f"   Symbols: {dataset['metadata']['num_symbols']}")
    print(f"   Orders: {dataset['metadata']['num_orders']}")
    print(f"   Trades: {dataset['metadata']['num_trades']}")
    print(f"   Anomalies: {dataset['metadata']['num_anomalies']}")


if __name__ == "__main__":
    main()
