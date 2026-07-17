# -*- coding: utf-8 -*-
import os

BASE = r'F:/JuShuiTan'

# ============================================================
# 1. Fix orders.html - add date filter + fix order detail
# ============================================================
path = os.path.join(BASE, 'templates', 'orders.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add date picker event listener after status filter
old_script = '''{% block scripts %}
<script>
let currentOrderId = '';'''
new_script = '''{% block scripts %}
<script>
let currentOrderId = '';

// 日期筛选
document.getElementById('datePicker').addEventListener('change', function() {
    window.location.href = '/orders?date=' + this.value;
});'''
content = content.replace(old_script, new_script)

# Fix showOrderDetail to actually call API
old_detail = '''function showOrderDetail(orderId) {
    currentOrderId = orderId;
    document.getElementById('orderDetailBody').innerHTML = '<p class="empty">加载中...</p>';
    document.getElementById('orderDetailModal').style.display = 'flex';
}'''
new_detail = '''async function showOrderDetail(orderId) {
    currentOrderId = orderId;
    document.getElementById('orderDetailBody').innerHTML = '<p class="empty">加载中...</p>';
    document.getElementById('orderDetailModal').style.display = 'flex';
    try {
        const res = await apiCall('/api/orders/' + encodeURIComponent(orderId));
        if (res && res.order_id) {
            document.getElementById('orderDetailBody').innerHTML = `
                <div style="display:grid; gap:10px; font-size:13px;">
                    <div><label>订单号:</label> <span>${res.order_id}</span></div>
                    <div><label>线上单号:</label> <span>${res.external_id || '-'}</span></div>
                    <div><label>店铺:</label> <span>${res.shop_name || res.shop_id || '-'}</span></div>
                    <div><label>类型:</label> <span>${res.order_type || '-'}</span></div>
                    <div><label>状态:</label> <span>${res.status || '-'}</span></div>
                    <div><label>商品数:</label> <span>${res.item_count || 0}</span></div>
                    <div><label>应付金额:</label> <span style="color:var(--accent-green)">¥${(res.pay_amount || 0).toFixed(2)}</span></div>
                    <div><label>运费:</label> <span>¥${(res.freight || 0).toFixed(2)}</span></div>
                    <div><label>采购成本:</label> <span style="color:var(--accent-orange)">¥${(res.purchase_cost || 0).toFixed(2)}</span></div>
                    <div><label>利润:</label> <span style="color:var(--accent-green)">¥${(res.profit || 0).toFixed(2)}</span></div>
                    <div><label>折扣:</label> <span>¥${(res.discount_amount || 0).toFixed(2)}</span></div>
                    <div><label>创建时间:</label> <span>${res.created_at || '-'}</span></div>
                    <div><label>付款时间:</label> <span>${res.paid_at || '-'}</span></div>
                    <div><label>发货时间:</label> <span>${res.shipped_at || '-'}</span></div>
                </div>`;
        } else {
            document.getElementById('orderDetailBody').innerHTML = '<p class="empty">订单不存在</p>';
        }
    } catch(e) {
        document.getElementById('orderDetailBody').innerHTML = '<p class="empty">加载失败: ' + e.message + '</p>';
    }
}'''
content = content.replace(old_detail, new_detail)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('orders.html: date filter + detail fixed')

# ============================================================
# 2. Fix index.html - add date range selectors
# ============================================================
path = os.path.join(BASE, 'templates', 'index.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add date range buttons next to date picker
old_header = '<input type="date" id="datePicker" value="{{ today }}" class="date-input">'
new_header = '''<div style="display:flex; gap:8px; align-items:center;">
            <input type="date" id="datePicker" value="{{ today }}" class="date-input">
            <div class="date-range-btns">
                <button onclick="loadDateRange(1)" class="btn btn-sm btn-outline">今日</button>
                <button onclick="loadDateRange(7)" class="btn btn-sm btn-outline">近7天</button>
                <button onclick="loadDateRange(30)" class="btn btn-sm btn-outline">近30天</button>
            </div>
        </div>'''
content = content.replace(old_header, new_header)

# Add loadDateRange function
old_date_handler = """document.getElementById('datePicker').addEventListener('change', function() {
    window.location.href = '/?date=' + this.value;
});"""
new_date_handler = """document.getElementById('datePicker').addEventListener('change', function() {
    window.location.href = '/?date=' + this.value;
});

// 加载指定天数的数据
function loadDateRange(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days + 1);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    window.location.href = `/?date_range=${startStr}_${endStr}&days=${days}`;
}"""
content = content.replace(old_date_handler, new_date_handler)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('index.html: date range added')

# ============================================================
# 3. Fix dashboard.html - add date picker + range
# ============================================================
path = os.path.join(BASE, 'templates', 'dashboard.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add date controls in title area
old_title = '''<div class="title-time" id="titleTime"></div>'''
new_title = '''<div style="display:flex; gap:8px; align-items:center; position:absolute; right:0; top:50%; transform:translateY(-50%);">
            <input type="date" id="dashDatePicker" class="date-input" style="width:140px;">
            <button onclick="loadDashRange(1)" class="btn btn-sm">今日</button>
            <button onclick="loadDashRange(7)" class="btn btn-sm">近7天</button>
            <button onclick="loadDashRange(30)" class="btn btn-sm">近30天</button>
            <span style="color:#7ec8e3; font-size:12px; margin-left:8px;" id="dashDateLabel"></span>
        </div>
        <div class="title-time" id="titleTime"></div>'''
content = content.replace(old_title, new_title)

# Add dashboard date handlers before the closing </script>
old_dash_script = '''    loadData();
    setInterval(loadData, 60000);'''
new_dash_script = '''    loadData();
    setInterval(loadData, 60000);
    
    // 日期选择器
    const dashPicker = document.getElementById('dashDatePicker');
    dashPicker.addEventListener('change', function() {
        loadDashData(this.value);
    });
    
    function loadDashRange(days) {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - days + 1);
        loadDashData(start.toISOString().slice(0, 10), end.toISOString().slice(0, 10));
        document.getElementById('dashDateLabel').textContent = `近${days}天`;
    }
    
    function loadDashData(startDate, endDate) {
        if (!endDate) endDate = startDate;
        const url = `/api/dashboard/data?start=${startDate}&end=${endDate}`;
        fetch(url).then(r => r.json()).then(data => {
            if (data) updateDashDisplay(data);
        });
    }
    
    function updateDashDisplay(data) {
        // 更新统计卡片
        if (data.total) {
            animateNumber('stat-orders', data.total.orders || data.total.total_orders || 0);
            animateNumber('stat-amount', data.total.amount || data.total.total_amount || 0);
            animateNumber('stat-profit', data.total.profit || data.total.total_profit || 0);
            animateNumber('stat-cost', data.total.cost || data.total.total_cost || 0);
        }
        if (data.today) {
            animateNumber('stat-today-orders', data.today.orders || 0);
            animateNumber('stat-today-amount', data.today.amount || 0);
        }
    }'''
content = content.replace(old_dash_script, new_dash_script)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('dashboard.html: date picker + range added')

print('All 4 issues fixed!')
