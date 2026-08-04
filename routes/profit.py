"""
利润统计路由 - 只统计分销订单
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
from models.database import get_connection

profit_bp = Blueprint('profit', __name__)


@profit_bp.route('/profit')
def profit_page():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('profit.html', today=today)


@profit_bp.route('/api/profit/summary')
def api_profit_summary():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' AND order_type NOT LIKE '%供销%' AND order_type NOT LIKE '%自发%' THEN 1 END) as total_orders,
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' THEN 1 END) as distribution_orders,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END), 0) as total_revenue,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as total_profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as platform_profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN freight ELSE 0 END), 0) as total_freight,
                CASE WHEN SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END) > 0
                    THEN ROUND(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END) * 100.0 /
                              SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END), 2)
                    ELSE 0 END as profit_rate
            FROM orders
            WHERE created_at LIKE ?
              AND status IN ('Sent', 'WaitOuterSent')
        """, (f"{date}%",)).fetchone()
        return jsonify(dict(row) if row else {})
    finally:
        conn.close()


@profit_bp.route('/api/profit/trend')
def api_profit_trend():
    days = int(request.args.get('days', 30))
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                substr(created_at, 1, 10) as date,
                COUNT(*) as total_orders,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(purchase_cost), 0) as total_cost,
                COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit,
                CASE WHEN SUM(pay_amount) > 0
                    THEN ROUND(SUM(pay_amount - purchase_cost) * 100.0 / SUM(pay_amount), 2)
                    ELSE 0 END as profit_rate
            FROM orders
            WHERE order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'
              AND status IN ('Sent', 'WaitOuterSent')
              AND created_at >= date('now', ?)
            GROUP BY date
            ORDER BY date
        """, (f"-{days} days",)).fetchall()
        return jsonify({'data': [dict(r) for r in rows]})
    finally:
        conn.close()


@profit_bp.route('/api/profit/by_shop')
def api_profit_by_shop():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                shop_name,
                COUNT(*) as order_count,
                COUNT(CASE WHEN order_type LIKE '%分销Plus%' THEN 1 END) as distribution_count,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END), 0) as revenue,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as cost,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END), 0) as profit,
                COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as platform_profit,
                CASE WHEN SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END) > 0
                    THEN ROUND(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN (pay_amount - purchase_cost) ELSE 0 END) * 100.0 /
                              SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN pay_amount ELSE 0 END), 2)
                    ELSE 0 END as profit_rate
            FROM orders
            WHERE created_at LIKE ?
              AND status IN ('Sent', 'WaitOuterSent')
            GROUP BY shop_name
            ORDER BY profit DESC
        """, (f"{date}%",)).fetchall()
        return jsonify({'data': [dict(r) for r in rows]})
    finally:
        conn.close()
