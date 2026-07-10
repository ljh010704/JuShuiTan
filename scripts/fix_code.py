# -*- coding: utf-8 -*-
import os, re

BASE = r'F:/JuShuiTan'

# === routes/profit.py ===
path = os.path.join(BASE, 'routes', 'profit.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '            FROM orders WHERE created_at LIKE ?'
new = '''            FROM orders
            WHERE created_at LIKE ?
              AND status NOT LIKE '%Cancel%'
              AND status NOT LIKE '%Returned%' '''
content = content.replace(old, new)

old2 = "COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,\n                CASE WHEN SUM"
new2 = "COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,\n                COALESCE(SUM(freight), 0) as total_freight,\n                CASE WHEN SUM"
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('profit.py updated')

print('Done')
