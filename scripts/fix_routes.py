# -*- coding: utf-8 -*-
import os

BASE = r'F:/JuShuiTan'

# ============================================================
# Fix models/database.py - add range query methods
# ============================================================
path = os.path.join(BASE, 'models', 'database.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add range query methods after get_stats_for_date
old_model = '''    @staticmethod
    def get_all(page=1, per_page=50):'''
new_model = '''    @staticmethod
    def get_stats_for_range(start_date, end_date):
        """获取日期范围内的统计数据"""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(pay_amount), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END), 0) as dist_amount,
                    COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost,
                    COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,
                    COUNT(CASE WHEN status LIKE '%Shipped%' OR status LIKE '%Sent%' THEN 1 END) as shipped_orders,
                    COUNT(CASE LIKE '%Finished%' OR status LIKE '%Completed%' THEN 1 END) as completed_orders,
                    COUNT(CASE WHEN status LIKE '%Cancel%' THEN 1 END) as cancelled_orders,
                    COUNT(CASE WHEN status IN ('WaitCheck', 'WaitSend', 'WaitOuterSent') THEN 1 END) as pending_orders
                FROM orders 
                WHERE substr(created_at, 1, 10) BETWEEN ? AND ?
            """, (start_date, end_date)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def get_by_range(start_date, end_date, page=1, per_page=50):
        """获取日期范围内的订单"""
        conn = get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM orders WHERE substr(created_at, 1, 10) BETWEEN ? AND ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (start_date, end_date, per_page, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def count_by_range(start_date, end_date):
        """获取日期范围内的订单总数"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE substr(created_at, 1, 10) BETWEEN ? AND ?",
                (start_date, end_date)
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    @staticmethod
    def get_all(page=1, per_page=50):'''
content = content.replace(old_model, new_model)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('database.py: range query methods added')

# ============================================================
# Fix routes/index.py - handle date_range param
# ============================================================
path = os.path.join(BASE, 'routes', 'index.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_index = '''@index_bp.route('/')
def dashboard():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    order_stats = OrderModel.get_stats_for_date(date)
    after_sale_stats = AfterSalesModel.get_stats_for_date(date)
    recent_stats = DailyStatsModel.get_recent(30)
    recent_orders = OrderModel.get_all(page=1, per_page=10)
    recent_after_sales = AfterSalesModel.get_all(page=1, per_page=10)
    sync_logs = SyncLogModel.get_recent(5)

    return render_template('index.html',
        today=date,
        order_stats=order_stats,
        after_sale_stats=after_sale_stats,
        recent_stats=recent_stats,
        recent_orders=recent_orders,
        recent_after_sales=recent_after_sales,
        sync_logs=sync_logs,
    )'''

new_index = '''@index_bp.route('/')
def dashboard():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    date_range = request.args.get('date_range', '')
    days = request.args.get('days', '')
    
    if date_range:
        start, end = date_range.split('_')
        order_stats = OrderModel.get_stats_for_range(start, end)
        after_sale_stats = AfterSalesModel.get_stats_for_range(start, end)
        recent_orders = OrderModel.get_by_range(start, end, page=1, per_page=10)
        recent_after_sales = AfterSalesModel.get_by_range(start, end, page=1, per_page=10)
    else:
        order_stats = OrderModel.get_stats_for_date(date)
        after_sale_stats = AfterSalesModel.get_stats_for_date(date)
        recent_orders = OrderModel.get_all(page=1, per_page=10)
        recent_after_sales = AfterSalesModel.get_all(page=1, per_page=10)
    
    recent_stats = DailyStatsModel.get_recent(int(days) if days else 30)
    sync_logs = SyncLogModel.get_recent(5)

    return render_template('index.html',
        today=date,
        order_stats=order_stats,
        after_sale_stats=after_sale_stats,
        recent_stats=recent_stats,
        recent_orders=recent_orders,
        recent_after_sales=recent_after_sales,
        sync_logs=sync_logs,
        date_range=date_range,
        days=days,
    )'''

content = content.replace(old_index, new_index)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('index.py: date_range handling added')

# ============================================================
# Fix routes/dashboard.py - add date range API
# ============================================================
path = os.path.join(BASE, 'routes', 'dashboard.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_dashboard_api = '''@dashboard_bp.route('/api/dashboard/data')
def api_dashboard_data():
    conn = get_connection()
    try:
        # 整体统计
        total = conn.execute("""
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' THEN 1 END) as dist_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost
            FROM orders
        """).fetchone()'''

new_dashboard_api = '''@dashboard_bp.route('/api/dashboard/data')
def api_dashboard_data():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    conn = get_connection()
    try:
        # 日期范围过滤条件
        date_filter = ""
        date_params = []
        if start and end:
            date_filter = " WHERE substr(created_at, 1, 10) BETWEEN ? AND ?"
            date_params = [start, end]
        
        # 整体统计
        total = conn.execute(f"""
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' THEN 1 END) as dist_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost
            FROM orders{date_filter}
        """, date_params).fetchone()'''

content = content.replace(old_dashboard_api, new_dashboard_api)

# Also fix the today_stats query in the same function
old_today = '''        # 今日统计
        today = datetime.now().strftime('%Y-%m-%d')
        today_stats = conn.execute("""
            SELECT
                COUNT(*) as orders,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as profit
            FROM orders WHERE created_at LIKE ?
        """, (f"{today}%",)).fetchone()'''
new_today = '''        # 统计天数
        if start and end:
            today_clause = "WHERE substr(created_at, 1, 10) BETWEEN ? AND ?"
            today_params = [start, end]
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            today_clause = "WHERE created_at LIKE ?"
            today_params = [f"{today}%"]
        today_stats = conn.execute(f"""
            SELECT
                COUNT(*) as orders,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as profit
            FROM orders {today_clause}
        """, today_params).fetchone()'''

content = content.replace(old_today, new_today)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('dashboard.py: date range API added')

print('All routes fixed!')
