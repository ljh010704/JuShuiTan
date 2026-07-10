import sqlite3
conn = sqlite3.connect('jushuitan.db')

# Check orders columns
cols = [r[1] for r in conn.execute('PRAGMA table_info(orders)').fetchall()]
print('orders columns:', cols)

# Check daily_stats columns
cols2 = [r[1] for r in conn.execute('PRAGMA table_info(daily_stats)').fetchall()]
print('daily_stats columns:', cols2)

# Add missing columns
if 'purchase_cost' not in cols:
    conn.execute('ALTER TABLE orders ADD COLUMN purchase_cost REAL DEFAULT 0')
    print('Added purchase_cost to orders')
if 'profit' not in cols:
    conn.execute('ALTER TABLE orders ADD COLUMN profit REAL DEFAULT 0')
    print('Added profit to orders')
if 'total_cost' not in cols2:
    conn.execute('ALTER TABLE daily_stats ADD COLUMN total_cost REAL DEFAULT 0')
    print('Added total_cost to daily_stats')
if 'total_profit' not in cols2:
    conn.execute('ALTER TABLE daily_stats ADD COLUMN total_profit REAL DEFAULT 0')
    print('Added total_profit to daily_stats')

conn.commit()
conn.close()
print('Done!')
