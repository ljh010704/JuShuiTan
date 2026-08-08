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


def _workbench_status(item):
    """售后工作台状态: auto(无需处理) / to_push(待推送供应商) / following(跟进中) / done(已完成)"""
    if (item.get('type') or '') == '仅退款' and (item.get('status') or '') != '已发货':
        return 'auto'  # 未发货仅退款，自动退款无需处理
    if (item.get('supplier_status') or '') == 'refunded':
        return 'done'
    if (item.get('status') or '') in ('Finished', 'Cancelled', 'Rejected'):
        return 'done'
    if (item.get('supplier_status') or '') == 'pushed':
        return 'following'
    if (item.get('status') or '') == 'Agreed':
        return 'following'
    return 'to_push'


def _waiting_days(item):
    """等待天数：已推送按推送时间算，未推送按申请时间算"""
    base = (item.get('supplier_pushed_at') or item.get('created_at') or '')[:19]
    try:
        dt = datetime.strptime(base, '%Y-%m-%d %H:%M:%S')
        return max((datetime.now() - dt).days, 0)
    except (ValueError, TypeError):
        return 0


def _annotate(items):
    for item in items:
        item['wb'] = _workbench_status(item)
        item['days'] = _waiting_days(item)
    return items


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
        items=_annotate(items),
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
        rows = conn.execute(
            "SELECT type, status, supplier_status, supplier_pushed_at, created_at FROM after_sales"
        ).fetchall()
        wb_counts = {'to_push': 0, 'following': 0, 'auto': 0, 'done': 0}
        overdue = 0
        for r in rows:
            item = dict(r)
            wb = _workbench_status(item)
            wb_counts[wb] += 1
            if wb == 'following' and _waiting_days(item) >= 3:
                overdue += 1
        return jsonify({
            'today_count': today['cnt'] if today else 0,
            'today_refund': today['refund'] if today else 0,
            'wb': wb_counts,
            'overdue': overdue,
        })
    finally:
        conn.close()


@after_sales_bp.route('/api/after-sales/supplier-status', methods=['POST'])
def api_set_supplier_status():
    """标记供应商跟进状态：pushed(已推送) / refunded(货款已回) / ''(重置)"""
    data = request.get_json() or {}
    after_sale_id = data.get('after_sale_id', '')
    status = data.get('status', '')
    if not after_sale_id:
        return jsonify({'success': False, 'message': '缺少售后单号'})
    if status not in ('', 'pushed', 'refunded'):
        return jsonify({'success': False, 'message': '无效状态'})
    AfterSalesModel.set_supplier_status(after_sale_id, status)
    msg = {
        'pushed': '已标记为「已推送供应商」',
        'refunded': '已标记为「货款已回」',
        '': '已重置为「待推送」',
    }[status]
    return jsonify({'success': True, 'message': msg})


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