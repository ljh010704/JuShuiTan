import sqlite3, json
conn = sqlite3.connect("F:/JuShuiTan/jushuitan.db")
cur = conn.cursor()

# Get top-level keys from first order
cur.execute("SELECT raw_data FROM orders LIMIT 1")
row = cur.fetchone()
if row and row[0]:
    d = json.loads(row[0])
    print("=== ALL TOP-LEVEL KEYS IN RAW_DATA ===")
    for k in sorted(d.keys()):
        print(f"  {k}: {type(d[k]).__name__} = {repr(d[k])[:100]}")

# Get distinct supplier data
print()
print("=== DISTINCT supplierName VALUES ===")
cur.execute("SELECT DISTINCT json_extract(raw_data, \"$.supplierName\") FROM orders")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()
print("=== DISTINCT supplierCoId VALUES ===")
cur.execute("SELECT DISTINCT json_extract(raw_data, \"$.supplierCoId\") FROM orders")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()
print("=== DISTINCT channelName VALUES ===")
cur.execute("SELECT DISTINCT json_extract(raw_data, \"$.channelName\") FROM orders")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()
print("=== DISTINCT channelCoId VALUES ===")
cur.execute("SELECT DISTINCT json_extract(raw_data, \"$.channelCoId\") FROM orders")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Count orders per supplier
print()
print("=== ORDERS PER SUPPLIER ===")
cur.execute("""
    SELECT json_extract(raw_data, \"$.supplierName\") as supplier,
           COUNT(*) as cnt,
           SUM(pay_amount) as total_pay,
           SUM(purchase_cost) as total_cost,
           SUM(profit) as total_profit
    FROM orders
    WHERE json_extract(raw_data, \"$.supplierName\") IS NOT NULL
      AND json_extract(raw_data, \"$.supplierName\") != \"\"
    GROUP BY supplier
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} orders, pay={r[2]}, cost={r[3]}, profit={r[4]}")

# Sample full raw_data with supplier info
print()
print("=== SAMPLE RAW_DATA (first order with supplier info) ===")
cur.execute("SELECT raw_data FROM orders WHERE json_extract(raw_data, \"$.supplierName\") IS NOT NULL AND json_extract(raw_data, \"$.supplierName\") != \"\" LIMIT 1")
row = cur.fetchone()
if row and row[0]:
    d = json.loads(row[0])
    # Print supplier-related fields
    supplier_keys = [k for k in d.keys() if "supplier" in k.lower() or "channel" in k.lower()]
    print("Supplier-related keys found:")
    for k in supplier_keys:
        print(f"  {k}: {d[k]}")
    
    # Also check nested goods list
    goods = d.get("disInnerOrderGoodsViewList", [])
    if goods:
        print()
        print(f"  disInnerOrderGoodsViewList has {len(goods)} items")
        if goods:
            print("  First goods item keys:", sorted(goods[0].keys()))
            # Check for supplier info in goods
            goods_supplier_keys = [k for k in goods[0].keys() if "supplier" in k.lower() or "vendor" in k.lower() or "source" in k.lower()]
            if goods_supplier_keys:
                print("  Supplier-related keys in goods:")
                for k in goods_supplier_keys:
                    print(f"    {k}: {goods[0][k]}")
            # Print all goods fields
            print("  All goods fields:")
            for k in sorted(goods[0].keys()):
                print(f"    {k}: {repr(goods[0][k])[:80]}")

# Check after_sales for supplier info
print()
print("=== AFTER_SALES RAW_DATA SAMPLE ===")
cur.execute("SELECT raw_data FROM after_sales LIMIT 1")
row = cur.fetchone()
if row and row[0]:
    d = json.loads(row[0])
    print("After sales keys:", sorted(d.keys()))
    supplier_keys = [k for k in d.keys() if "supplier" in k.lower() or "channel" in k.lower()]
    if supplier_keys:
        print("Supplier-related keys:", supplier_keys)
        for k in supplier_keys:
            print(f"  {k}: {d[k]}")

conn.close()

