import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jushuitan.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Show sample data before fix
print("Before fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print(f"  order_id={row[0]}, pay={row[1]}, cost={row[2]}, profit={row[3]}")

# Fix: swap purchase_cost and profit, then recalculate profit
# Old mapping: purchase_cost = purchaseAmt (wrong), profit = drpAmount
# New mapping: purchase_cost = drpAmount (old profit value), profit = pay_amount - drpAmount
cursor.execute("""
    UPDATE orders SET 
        purchase_cost = profit,
        profit = pay_amount - profit
    WHERE profit != 0
""")

conn.commit()

print("\nAfter fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print(f"  order_id={row[0]}, pay={row[1]}, cost={row[2]}, profit={row[3]}")

# Verify with order 686139
print("\nOrder 686139:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders WHERE order_id = '686139'").fetchall():
    print(f"  pay={row[1]}, cost={row[2]}, profit={row[3]}")

conn.close()
print("\nDone!")