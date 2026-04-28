"""Round 4 Data Analysis - Comprehensive"""
import csv
from collections import defaultdict

# Analyze all 3 days
for day in [1, 2, 3]:
    fn = f'D:/PROSPERITY/round4/data/ROUND_4/prices_round_4_day_{day}.csv'
    products = set()
    first_ts = {}
    last_ts = {}
    mid_prices = defaultdict(list)
    
    with open(fn, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            p = row['product']
            products.add(p)
            mp = float(row['mid_price'])
            mid_prices[p].append(mp)
            if p not in first_ts:
                first_ts[p] = mp
            last_ts[p] = mp
    
    print(f'\n=== DAY {day} ===')
    for p in sorted(products):
        prices = mid_prices[p]
        mn = min(prices)
        mx = max(prices)
        avg = sum(prices) / len(prices)
        change = last_ts[p] - first_ts[p]
        print(f'  {p:25s}: start={first_ts[p]:10.1f}  end={last_ts[p]:10.1f}  chg={change:+8.1f}  avg={avg:10.1f}  range=[{mn:.1f}, {mx:.1f}]')

# Analyze trades - who are the market participants?
print('\n\n=== TRADE ANALYSIS (ALL 3 DAYS) ===')
for day in [1, 2, 3]:
    fn = f'D:/PROSPERITY/round4/data/ROUND_4/trades_round_4_day_{day}.csv'
    buyer_counts = defaultdict(int)
    seller_counts = defaultdict(int)
    product_volume = defaultdict(int)
    product_trades = defaultdict(int)
    
    with open(fn, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            buyer = row['buyer']
            seller = row['seller']
            symbol = row['symbol']
            qty = int(row['quantity'])
            buyer_counts[buyer] += qty
            seller_counts[seller] += qty
            product_volume[symbol] += qty
            product_trades[symbol] += 1
    
    print(f'\n--- Day {day} ---')
    print('  Product volumes:')
    for p in sorted(product_volume.keys()):
        print(f'    {p:25s}: {product_volume[p]:6d} units across {product_trades[p]:4d} trades')
    
    all_participants = set(list(buyer_counts.keys()) + list(seller_counts.keys()))
    print('  Participant activity (buy_vol / sell_vol):')
    for part in sorted(all_participants):
        print(f'    {part:12s}: buy={buyer_counts.get(part,0):6d}  sell={seller_counts.get(part,0):6d}')

# Analyze Mark 01 and Mark 22 VEV trading patterns specifically
print('\n\n=== MARK 01 vs MARK 22 VEV OPTIONS TRADING ===')
for day in [1, 2, 3]:
    fn = f'D:/PROSPERITY/round4/data/ROUND_4/trades_round_4_day_{day}.csv'
    print(f'\n--- Day {day} ---')
    with open(fn, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if 'VEV' in row['symbol'] and ('Mark 01' in row['buyer'] or 'Mark 01' in row['seller']):
                if row['buyer'] == 'Mark 01':
                    direction = 'BUY'
                else:
                    direction = 'SELL'
                print(f'  ts={row["timestamp"]:>7s}  {direction:4s}  {row["symbol"]:12s}  price={float(row["price"]):7.1f}  qty={row["quantity"]}  counterparty={row["seller"] if direction=="BUY" else row["buyer"]}')

# Analyze VEV_4000 price correlation with VELVETFRUIT_EXTRACT
print('\n\n=== VEV INTRINSIC VALUE vs MID PRICE ===')
for day in [1, 2, 3]:
    fn = f'D:/PROSPERITY/round4/data/ROUND_4/prices_round_4_day_{day}.csv'
    ve_prices = {}
    vev_prices = defaultdict(dict)
    
    with open(fn, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            ts = int(row['timestamp'])
            p = row['product']
            mp = float(row['mid_price'])
            if p == 'VELVETFRUIT_EXTRACT':
                ve_prices[ts] = mp
            elif p.startswith('VEV_'):
                vev_prices[p][ts] = mp
    
    print(f'\n--- Day {day} (sampled every 10000 ticks) ---')
    strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
    # TTE = 7 - day + 1 (in Solvenarian days)
    tte = 7 - day + 1  # day 1 -> TTE 7, day 2 -> TTE 6, day 3 -> TTE 5
    print(f'  TTE = {tte} days')
    
    for ts in sorted(ve_prices.keys()):
        if ts % 100000 != 0:
            continue
        ve = ve_prices[ts]
        line = f'  ts={ts:>7d}  VE={ve:.0f}'
        for strike in strikes:
            vev_name = f'VEV_{strike}'
            if ts in vev_prices[vev_name]:
                vev_mid = vev_prices[vev_name][ts]
                intrinsic = max(0, ve - strike)
                time_value = vev_mid - intrinsic
                line += f'  {strike}:mid={vev_mid:.0f}/iv={intrinsic:.0f}/tv={time_value:.0f}'
        print(line)

print('\n\n=== HYDROGEL_PACK DETAILED ANALYSIS ===')
for day in [1, 2, 3]:
    fn = f'D:/PROSPERITY/round4/data/ROUND_4/prices_round_4_day_{day}.csv'
    hp_prices = []
    with open(fn, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['product'] == 'HYDROGEL_PACK':
                hp_prices.append(float(row['mid_price']))
    avg = sum(hp_prices) / len(hp_prices)
    print(f'  Day {day}: avg={avg:.1f}  min={min(hp_prices):.1f}  max={max(hp_prices):.1f}  samples={len(hp_prices)}')
