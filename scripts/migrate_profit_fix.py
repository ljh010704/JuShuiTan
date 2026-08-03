import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jushuitan.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Before fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print("  order_id=%s, pay=%s, cost=%s, profit=%s" % row)

cursor.execute("""
    UPDATE orders SET 
        purchase_cost = profit,
        profit = pay_amount - profit
    WHERE profit != 0
""")

conn.commit()

print("\nAfter fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print("  order_id=%s, pay=%s, cost=%s, profit=%s" % row)

print("\nOrder 686139:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders WHERE order_id = '686139'").fetchall():
    print("  pay=%s, cost=%s, profit=%s" % row)

conn.close()
print("\nDone!")