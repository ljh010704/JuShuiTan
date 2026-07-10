"""
订单管理路由
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
from models.database import OrderModel

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/orders')
def orders_page():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    date = request.args.get('date', '')
    status = request.args.get('status', '')

    if date:
        orders = OrderModel.get_by_date(date)
    else:
        orders = OrderModel.get_all(page=page, per_page=per_page)

    total = OrderModel.count()

    return render_template('orders.html',
        orders=orders,
        total=total,
        page=page,
        per_page=per_page,
        current_date=date,
        current_status=status,
    )


@orders_bp.route('/api/orders')
def api_orders():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    date = request.args.get('date', '')

    if date:
        orders = OrderModel.get_by_date(date)
    else:
        orders = OrderModel.get_all(page=page, per_page=per_page)

    total = OrderModel.count()
    return jsonify({
        'data': orders,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@orders_bp.route('/api/orders/stats')
def api_order_stats():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    stats = OrderModel.get_stats_for_date(date)
    return jsonify(stats)



@orders_bp.route('/api/orders/export.xlsx')
def export_orders_xlsx():
    from openpyxl import Workbook
    from flask import send_file, request, Response
    from io import BytesIO
    from datetime import datetime

    date = request.args.get('date', '')
    if date:
        orders = OrderModel.get_by_date(date)
    else:
        orders = OrderModel.get_all(page=1, per_page=100000)

    wb = Workbook()
    ws = wb.active
    ws.title = '\u8ba2\u5355\u660e\u7ec6'
    headers = ['\u8ba2\u5355\u53f7','\u7ebf\u4e0a\u5355\u53f7','\u5e97\u94fa','\u5546\u54c1\u6570','\u5e94\u4ed8\u91d1\u989d','\u8fd0\u8d39','\u72b6\u6001','\u521b\u5efa\u65f6\u95f4']
    ws.append(headers)
    for order in (orders or []):
        ws.append([
            order.get('order_id',''),
            order.get('external_id',''),
            order.get('shop_name','') or order.get('shop_id',''),
            order.get('item_count',0),
            order.get('pay_amount',0),
            order.get('freight',0),
            order.get('status',''),
            order.get('created_at',''),
        ])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = (date or datetime.now().strftime('%Y-%m-%d')) + '.xlsx'
    return send_file(bio, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@orders_bp.route('/api/orders/<order_id>')
def api_order_detail(order_id):
    order = OrderModel.get_by_id(order_id)
    if not order:
        return jsonify({'error': '?????'}), 404
    return jsonify(order)
