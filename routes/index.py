"""
首页统计看板路由
"""
import logging
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
from models.database import OrderModel, AfterSalesModel, DailyStatsModel, SyncLogModel, get_connection

index_bp = Blueprint('index', __name__)
logger = logging.getLogger(__name__)

DIST_FILTER = """order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'"""

STATUS_NAME_MAP = {
    'Sent': '已发货',
    'WaitOuterSent': '待发货',
    'Cancelled': '已取消',
    'Question': '异常',
    'Split': '已拆分',
    'Merged': '已合并',
    'WaitConfirm': '待确认',
}


def _scope_clause(date, date_range):
    """返回 (where_sql, params)，限定 created_at 范围"""
    if date_range:
        parts = date_range.split('_')
        if len(parts) == 2:
            return "substr(created_at,1,10) BETWEEN ? AND ?", [parts[0], parts[1]]
    return "created_at LIKE ?", [f"{date}%"]


@index_bp.route('/')
def dashboard():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    date_range = request.args.get('date_range', '')
    days = request.args.get('days', '')

    clause, params = _scope_clause(date, date_range)

    if date_range and len(date_range.split('_')) == 2:
        start, end = date_range.split('_')
        order_stats = OrderModel.get_stats_for_range(start, end)
        after_sale_stats = AfterSalesModel.get_stats_for_range(start, end)
        recent_after_sales = AfterSalesModel.get_by_range(start, end, page=1, per_page=10)
    else:
        order_stats = OrderModel.get_stats_for_date(date)
        after_sale_stats = AfterSalesModel.get_stats_for_date(date)
        recent_after_sales = AfterSalesModel.get_all(page=1, per_page=10)

    try:
        days_n = int(days) if days else 30
    except (ValueError, TypeError):
        days_n = 30

    conn = get_connection()
    try:
        recent_orders = [dict(r) for r in conn.execute(f"""
            SELECT * FROM orders
            WHERE {DIST_FILTER} AND {clause}
            ORDER BY created_at DESC LIMIT 10
        """, params).fetchall()]

        recent_stats = [dict(r) for r in conn.execute(f"""
            SELECT substr(created_at, 1, 10) as date,
                COUNT(*) as total_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(purchase_cost), 0) as total_cost,
                COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit
            FROM orders
            WHERE {DIST_FILTER}
              AND status IN ('Sent', 'WaitOuterSent')
              AND created_at >= date('now', 'localtime', ?)
            GROUP BY date ORDER BY date
        """, (f"-{days_n} days",)).fetchall()]

        status_rows = conn.execute(f"""
            SELECT status, COUNT(*) as cnt FROM orders
            WHERE {DIST_FILTER} AND {clause}
            GROUP BY status ORDER BY cnt DESC
        """, params).fetchall()
    finally:
        conn.close()

    status_map = {r['status']: r['cnt'] for r in status_rows}
    order_stats['shipped_orders'] = status_map.get('Sent', 0)
    order_stats['pending_orders'] = status_map.get('WaitOuterSent', 0)
    order_stats['cancelled_orders'] = status_map.get('Cancelled', 0)

    status_dist = [
        {'name': STATUS_NAME_MAP.get(r['status'], r['status'] or '未知'), 'value': r['cnt']}
        for r in status_rows
    ]

    sync_logs = SyncLogModel.get_recent(5)

    return render_template('index.html',
        today=date,
        order_stats=order_stats,
        after_sale_stats=after_sale_stats,
        recent_stats=recent_stats,
        recent_orders=recent_orders,
        recent_after_sales=recent_after_sales,
        status_dist=status_dist,
        sync_logs=sync_logs,
        date_range=date_range,
        days=days,
    )


def _get_trend(days):
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(f"""
            SELECT substr(created_at, 1, 10) as date,
                COUNT(*) as total_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(purchase_cost), 0) as total_cost,
                COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit
            FROM orders
            WHERE {DIST_FILTER}
              AND status IN ('Sent', 'WaitOuterSent')
              AND created_at >= date('now', 'localtime', ?)
            GROUP BY date ORDER BY date
        """, (f"-{days} days",)).fetchall()]
    finally:
        conn.close()


@index_bp.route('/api/dashboard')
def api_dashboard():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    order_stats = OrderModel.get_stats_for_date(date)
    after_sale_stats = AfterSalesModel.get_stats_for_date(date)
    return jsonify({
        'date': date,
        'order_stats': order_stats,
        'after_sale_stats': after_sale_stats,
        'trend_data': _get_trend(30),
    })


@index_bp.route('/api/trend')
def api_trend():
    try:
        days = int(request.args.get('days', 30))
    except (ValueError, TypeError):
        days = 30
    return jsonify({'data': _get_trend(days)})
