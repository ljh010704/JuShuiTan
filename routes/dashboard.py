"""
数据大屏路由
"""
import logging
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
from models.database import get_connection

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)


@dashboard_bp.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/data')
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

        status_filter = " WHERE status IN ('Sent', 'WaitOuterSent')"
        if date_filter:
            status_filter = " AND status IN ('Sent', 'WaitOuterSent')"
        order_filter = " WHERE order_type LIKE '%分销Plus%' AND order_type NOT LIKE '%供销%' AND order_type NOT LIKE '%自发%'"
        if date_filter or status_filter:
            order_filter = " AND order_type LIKE '%分销Plus%' AND order_type NOT LIKE '%供销%' AND order_type NOT LIKE '%自发%'"

        # 整体统计
        total = conn.execute(f"""
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' THEN 1 END) as dist_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as total_profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost
            FROM orders{date_filter}{status_filter}{order_filter}
        """, date_params).fetchone()

        # 日期范围统计
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
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as profit
            FROM orders {today_clause}
              AND status IN ('Sent', 'WaitOuterSent')
              AND order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'
        """, today_params).fetchone()

        # 按店铺统计
        shops = conn.execute("""
            SELECT
                shop_name,
                COUNT(*) as order_count,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as profit
            FROM orders
            WHERE status IN ('Sent', 'WaitOuterSent')
              AND order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'
            GROUP BY shop_name
            ORDER BY amount DESC
            LIMIT 10
        """).fetchall()

        # 趋势数据（根据日期范围动态分组）
        if start and end:
            date_clause = " AND substr(created_at,1,10) BETWEEN ? AND ?"
            date_params = [start, end]
        else:
            date_clause = ""
            date_params = []
        
        # 计算日期范围天数
        if start and end:
            from datetime import datetime
            d1 = datetime.strptime(start, '%Y-%m-%d')
            d2 = datetime.strptime(end, '%Y-%m-%d')
            days = (d2 - d1).days
        else:
            days = 365
        
        # 根据范围选择分组方式
        if days <= 1:
            # 按小时
            group_by = "substr(created_at, 1, 13)"
            label_format = "hour"
        elif days <= 31:
            # 按天
            group_by = "substr(created_at, 1, 10)"
            label_format = "day"
        elif days <= 90:
            # 按周
            group_by = "strftime('%Y-W%w', created_at)"
            label_format = "week"
        else:
            # 按月
            group_by = "substr(created_at, 1, 7)"
            label_format = "month"
        
        monthly = conn.execute(f"""
            SELECT
                {group_by} as period,
                COUNT(*) as orders,
                COALESCE(SUM(pay_amount), 0) as amount,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as profit
            FROM orders WHERE created_at != ""
              AND status IN ('Sent', 'WaitOuterSent')
              AND order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'
              {date_clause}
            GROUP BY period
            ORDER BY period
        """, date_params).fetchall()

        # 订单状态分布
        status_dist = conn.execute("""
            SELECT status, COUNT(*) as cnt FROM orders 
            WHERE order_type LIKE '%分销Plus%' 
              AND order_type NOT LIKE '%供销%' 
              AND order_type NOT LIKE '%自发%'
            GROUP BY status ORDER BY cnt DESC LIMIT 5
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