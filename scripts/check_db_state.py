import sqlite3

DB_PATH = "/home/JuShuiTan/jushuitan.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 先检查当前状态
print("Current state (sample):")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 5").fetchall():
    print("  order_id=%s, pay=%s, cost=%s, profit=%s" % (row[0], row[1], row[2], row[3]))

# 统计总数
total = cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
print("\nTotal orders: %s" % total)

conn.close()