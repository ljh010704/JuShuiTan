import sqlite3

DB_PATH = "/home/JuShuiTan/jushuitan.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 先恢复：把现在的 profit 和 purchase_cost 交换回来（因为之前的脚本已经运行了2次，数据被交换了2次，等于没变）
# 然后重新计算 profit = pay_amount - purchase_cost

print("Before fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print("  order_id=%s, pay=%s, cost=%s, profit=%s" % (row[0], row[1], row[2], row[3]))

# 恢复原始值：purchase_cost = profit, profit = pay_amount - profit
cursor.execute("""
    UPDATE orders SET 
        purchase_cost = profit,
        profit = pay_amount - profit
""")

conn.commit()

print("\nAfter fix:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders LIMIT 3").fetchall():
    print("  order_id=%s, pay=%s, cost=%s, profit=%s" % (row[0], row[1], row[2], row[3]))

# 验证 686139
print("\nOrder 686139:")
for row in cursor.execute("SELECT order_id, pay_amount, purchase_cost, profit FROM orders WHERE order_id = '686139'").fetchall():
    print("  pay=%s, cost=%s, profit=%s" % (row[1], row[2], row[3]))

# 统计
stats = cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as profit_orders,
        SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as loss_orders,
        SUM(profit) as total_profit,
        AVG(profit) as avg_profit
    FROM orders WHERE status IN ('Sent', 'WaitOuterSent')
""").fetchone()

print("\nStatistics (Sent + WaitOuterSent):")
print("  Total orders: %s" % stats[0])
print("  Profitable orders: %s" % stats[1])
print("  Loss orders: %s" % stats[2])
print("  Total profit: %.2f" % stats[3])
print("  Average profit: %.2f" % stats[4])

conn.close()
print("\nDone!")