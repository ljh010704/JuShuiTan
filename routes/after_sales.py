"""
售后管理路由
"""
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
from models.database import AfterSalesModel

after_sales_bp = Blueprint('after_sales', __name__)


@after_sales_bp.route('/after-sales')
def after_sales_page():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    date = request.args.get('date', '')
    status = request.args.get('status', '')

    if date:
        items = AfterSalesModel.get_by_date(date)
    else:
        items = AfterSalesModel.get_all(page=page, per_page=per_page)

    total = AfterSalesModel.count()

    return render_template('after_sales.html',
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        current_date=date,
        current_status=status,
    )


@after_sales_bp.route('/api/after-sales')
def api_after_sales():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    date = request.args.get('date', '')

    if date:
        items = AfterSalesModel.get_by_date(date)
    else:
        items = AfterSalesModel.get_all(page=page, per_page=per_page)

    total = AfterSalesModel.count()
    return jsonify({
        'data': items,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@after_sales_bp.route('/api/after-sales/stats')
def api_after_sale_stats():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    stats = AfterSalesModel.get_stats_for_date(date)
    return jsonify(stats)


@after_sales_bp.route('/api/after-sales/export.xlsx')
def export_after_sales_xlsx():
    from openpyxl import Workbook
    from flask import send_file
    from io import BytesIO

    date = request.args.get('date', '')
    if date:
        items = AfterSalesModel.get_by_date(date)
    else:
        items = AfterSalesModel.get_all(page=1, per_page=100000)

    wb = Workbook()
    ws = wb.active
    ws.title = 'AfterSales'
    headers = ['after_sale_id', 'order_id', 'shop_name', 'type', 'amount', 'quantity', 'reason', 'status', 'created_at']
    ws.append(headers)
    for item in (items or []):
        ws.append([
            item.get('after_sale_id', ''),
            item.get('external_id', '') or item.get('order_id', ''),
            item.get('shop_name', ''),
            item.get('type', ''),
            item.get('amount', 0),
            item.get('quantity', 0),
            item.get('reason', ''),
            item.get('status', ''),
            item.get('created_at', ''),
        ])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = (date or datetime.now().strftime('%Y-%m-%d')) + '_after_sales.xlsx'
    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
