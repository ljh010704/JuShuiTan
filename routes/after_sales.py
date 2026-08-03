"""
售后管理路由
"""
import logging
from flask import Blueprint, render_template, jsonify, request, send_file
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from models.database import AfterSalesModel, get_connection

after_sales_bp = Blueprint('after_sales', __name__)
logger = logging.getLogger(__name__)


@after_sales_bp.route('/after-sales')
def after_sales_page():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
    except (ValueError, TypeError):
        page = 1
        per_page = 50
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
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
    except (ValueError, TypeError):
        page = 1
        per_page = 50
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
    conn = get_connection()
    try:
        today = conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as refund FROM after_sales WHERE created_at LIKE ?",
            (f"{date}%",)
        ).fetchone()
        pending = conn.execute(
            "SELECT COUNT(*) as cnt FROM after_sales WHERE status IN ('WaitCheck', 'WaitOuterSent')"
        ).fetchone()
        total = conn.execute("SELECT COUNT(*) as cnt FROM after_sales").fetchone()
        return jsonify({
            'today_count': today['cnt'] if today else 0,
            'today_refund': today['refund'] if today else 0,
            'pending_count': pending['cnt'] if pending else 0,
            'total_count': total['cnt'] if total else 0,
        })
    finally:
        conn.close()


@after_sales_bp.route('/api/after-sales/export.xlsx')
def export_after_sales_xlsx():
    """流式导出售后 Excel，避免内存溢出"""
    date = request.args.get('date', '')
    if date:
        items = AfterSalesModel.get_by_date(date)
    else:
        # 限制最大导出数量
        items = AfterSalesModel.get_all(page=1, per_page=50000)

    wb = Workbook()
    ws = wb.active
    ws.title = '售后明细'
    headers = ['售后单号', '订单号', '店铺', '类型', '金额', '数量', '原因', '状态', '创建时间']
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