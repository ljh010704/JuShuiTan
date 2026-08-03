import sqlite3

DB_PATH = "/home/JuShuiTan/jushuitan.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== 1. 检查订单类型分布 ===")
for row in cursor.execute("SELECT order_type, COUNT(*) as cnt FROM orders GROUP BY order_type ORDER BY cnt DESC").fetchall():
    print("  %s: %s" % (row[0][:50], row[1]))

print("\n=== 2. 检查分销订单的状态分布 ===")
for row in cursor.execute("""
    SELECT status, COUNT(*) as cnt FROM orders 
    WHERE order_type LIKE '%分销Plus%' 
      AND order_type NOT LIKE '%供销%' 
      AND order_type NOT LIKE '%自发%'
    GROUP BY status ORDER BY cnt DESC
""").fetchall():
    print("  %s: %s" % (row[0], row[1]))

print("\n=== 3. 检查所有订单的状态分布 ===")
for row in cursor.execute("SELECT status, COUNT(*) as cnt FROM orders GROUP BY status ORDER BY cnt DESC").fetchall():
    print("  %s: %s" % (row[0], row[1]))

print("\n=== 4. 检查总订单数 ===")
total = cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
print("  总订单数: %s" % total)

dist = cursor.execute("SELECT COUNT(*) FROM orders WHERE order_type LIKE '%分销Plus%'").fetchone()[0]
print("  分销订单数: %s" % dist)

conn.close()