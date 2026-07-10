"""
首页统计看板路由
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
from models.database import OrderModel, AfterSalesModel, DailyStatsModel, SyncLogModel

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
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
    )


@index_bp.route('/api/dashboard')
def api_dashboard():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    order_stats = OrderModel.get_stats_for_date(date)
    after_sale_stats = AfterSalesModel.get_stats_for_date(date)
    recent_stats = DailyStatsModel.get_recent(30)
    return jsonify({
        'date': date,
        'order_stats': order_stats,
        'after_sale_stats': after_sale_stats,
        'trend_data': recent_stats,
    })


@index_bp.route('/api/trend')
def api_trend():
    days = int(request.args.get('days', 30))
    stats = DailyStatsModel.get_recent(days)
    return jsonify({'data': stats})
