"""
数据大屏路由
"""
from flask import Blueprint, render_template, jsonify
from datetime import datetime
from models.database import get_connection

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/data')
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
        """).fetchone()

        # 今日统计
        today = datetime.now().strftime('%Y-%m-%d')
        today_stats = conn.execute("""
            SELECT
                COUNT(*) as orders,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as profit
            FROM orders WHERE created_at LIKE ?
        """, (f"{today}%",)).fetchone()

        # 按店铺统计
        shops = conn.execute("""
            SELECT
                shop_name,
                COUNT(*) as order_count,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as profit
            FROM orders
            GROUP BY shop_name
            ORDER BY amount DESC
            LIMIT 10
        """).fetchall()

        # 按月趋势
        monthly = conn.execute("""
            SELECT
                substr(created_at, 1, 7) as month,
                COUNT(*) as orders,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as profit
            FROM orders WHERE created_at != ""
            GROUP BY month
            ORDER BY month
        """).fetchall()

        # 订单状态分布
        status_dist = conn.execute("""
            SELECT status, COUNT(*) as cnt FROM orders GROUP BY status ORDER BY cnt DESC LIMIT 5
        """).fetchall()

        # 售后统计
        after_sale = conn.execute("""
            SELECT COUNT(*) as total, COALESCE(SUM(amount), 0) as refund_amount FROM after_sales
        """).fetchone()

        return jsonify({
            'total': dict(total),
            'today': dict(today_stats),
            'shops': [dict(r) for r in shops],
            'monthly': [dict(r) for r in monthly],
            'status': [dict(r) for r in status_dist],
            'after_sale': dict(after_sale),
        })
    finally:
        conn.close()
