# -*- coding: utf-8 -*-
import os

BASE = r'F:/JuShuiTan/templates'

# ============================================================
# 1. sync.html - Fix to use background polling
# ============================================================
path = os.path.join(BASE, 'sync.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_script = '''{% block scripts %}
<script>
async function syncData(type) {
    const statusEl = document.getElementById('syncStatus');
    const statusText = document.getElementById('syncStatusText');
    const statusDetail = document.getElementById('syncStatusDetail');
    statusEl.style.display = 'flex';
    statusText.textContent = '同步中，请勿关闭页面...';
    statusDetail.textContent = '';

    document.querySelectorAll('.sync-card .btn').forEach(b => b.disabled = true);

    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        if (res.success) {
            statusText.textContent = res.message;
            statusDetail.textContent = '全部帐号同步成功';
            setTimeout(() => location.reload(), 1500);
        } else if (res.count > 0) {
            statusText.textContent = res.message;
            statusDetail.textContent = '存在部分失败，请查看同步记录详情';
        } else {
            statusText.textContent = '失败: ' + res.message;
            statusDetail.textContent = '请检查网络、登录状态或帐号配置';
        }
    } catch(e) {
        statusText.textContent = '请求失败: ' + e.message;
        statusDetail.textContent = '前端请求异常，请重试';
    } finally {
        document.querySelectorAll('.sync-card .btn').forEach(b => b.disabled = false);
    }
}
</script>
{% endblock %}'''

new_script = '''{% block scripts %}
<script>
let syncPollTimer = null;

async function syncData(type) {
    const statusEl = document.getElementById('syncStatus');
    const statusText = document.getElementById('syncStatusText');
    const statusDetail = document.getElementById('syncStatusDetail');
    statusEl.style.display = 'flex';
    statusText.textContent = '正在启动同步...';
    statusDetail.textContent = '';

    document.querySelectorAll('.sync-card .btn').forEach(b => { b.disabled = true; b.dataset.origText = b.textContent; b.textContent = '同步中...'; });

    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        if (res.success) {
            statusText.textContent = res.message || '同步已启动';
            statusDetail.textContent = '后台同步进行中，请勿关闭页面';
            startSyncPoll();
        } else {
            statusText.textContent = '启动失败: ' + (res.message || '未知错误');
            statusDetail.textContent = '请检查网络或服务器状态';
            document.querySelectorAll('.sync-card .btn').forEach(b => { b.disabled = false; b.textContent = b.dataset.origText || '同步'; });
        }
    } catch(e) {
        statusText.textContent = '请求失败: ' + e.message;
        statusDetail.textContent = '前端请求异常，请重试';
        document.querySelectorAll('.sync-card .btn').forEach(b => { b.disabled = false; b.textContent = b.dataset.origText || '同步'; });
    }
}

function startSyncPoll() {
    if (syncPollTimer) clearInterval(syncPollTimer);
    const statusText = document.getElementById('syncStatusText');
    const statusDetail = document.getElementById('syncStatusDetail');

    syncPollTimer = setInterval(async () => {
        try {
            const res = await fetch('/api/sync/status');
            const data = await res.json();
            if (!data.running) {
                clearInterval(syncPollTimer);
                syncPollTimer = null;
                statusText.textContent = '同步完成！';
                statusDetail.textContent = '数据已更新，即将刷新页面...';
                document.querySelectorAll('.sync-card .btn').forEach(b => { b.disabled = false; b.textContent = b.dataset.origText || '同步'; });
                setTimeout(() => location.reload(), 2000);
            }
        } catch(e) {
            // ignore poll errors
        }
    }, 5000);
}
</script>
{% endblock %}'''

content = content.replace(old_script, new_script)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('sync.html updated')

# ============================================================
# 2. index.html - Fix sync button to use polling
# ============================================================
path = os.path.join(BASE, 'index.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_sync = '''// 同步数据
async function syncData(type) {
    const btn = document.getElementById('syncBtn');
    btn.disabled = true;
    btn.textContent = '同步中...';
    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        alert(res.message || '同步完成');
        if (res.success) location.reload();
    } catch(e) {
        alert('同步失败: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '同步数据';
    }
}'''

new_sync = '''// 同步数据 - 后台轮询
async function syncData(type) {
    const btn = document.getElementById('syncBtn');
    btn.disabled = true;
    btn.textContent = '同步中...';
    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        if (res.success) {
            btn.textContent = '后台同步中...';
            startSyncPolls();
        } else {
            alert('同步启动失败: ' + (res.message || '未知错误'));
            btn.disabled = false;
            btn.textContent = '同步数据';
        }
    } catch(e) {
        alert('同步失败: ' + e.message);
        btn.disabled = false;
        btn.textContent = '同步数据';
    }
}

let syncPollTimers = null;
function startSyncPolls() {
    if (syncPollTimers) clearInterval(syncPollTimers);
    const btn = document.getElementById('syncBtn');
    syncPollTimers = setInterval(async () => {
        try {
            const res = await fetch('/api/sync/status');
            const data = await res.json();
            if (!data.running) {
                clearInterval(syncPollTimers);
                syncPollTimers = null;
                btn.disabled = false;
                btn.textContent = '同步数据';
                location.reload();
            }
        } catch(e) {}
    }, 5000);
}'''

content = content.replace(old_sync, new_sync)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('index.html updated')

# ============================================================
# 3. suppliers.html - Fix sync polling
# ============================================================
path = os.path.join(BASE, 'suppliers.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_sup_sync = '''async function syncSuppliers() {
    const btn = document.getElementById('syncBtn');
    const statusEl = document.getElementById('syncStatus');
    const statusText = document.getElementById('syncStatusText');

    btn.disabled = true;
    btn.textContent = '同步中...';
    statusEl.style.display = 'block';
    statusText.textContent = '正在从聚水潭同步供应商数据...';

    try {
        const data = await apiCall('/api/sync', 'POST', {type: 'full'});
        statusText.textContent = data.message || '同步完成';
        setTimeout(() => {
            statusEl.style.display = 'none';
            loadData();
        }, 2000);
    } catch(e) {
        statusText.textContent = '同步失败: ' + (e && e.message ? e.message : e);
    } finally {
        btn.disabled = false;
        btn.textContent = '同步供应商';
    }
}'''

new_sup_sync = '''async function syncSuppliers() {
    const btn = document.getElementById('syncBtn');
    const statusEl = document.getElementById('syncStatus');
    const statusText = document.getElementById('syncStatusText');

    btn.disabled = true;
    btn.textContent = '同步中...';
    statusEl.style.display = 'block';
    statusText.textContent = '正在启动同步...';

    try {
        const data = await apiCall('/api/sync', 'POST', {type: 'full'});
        if (data.success) {
            statusText.textContent = '后台同步进行中...';
            startSupplierPoll();
        } else {
            statusText.textContent = '启动失败: ' + (data.message || '未知错误');
            btn.disabled = false;
            btn.textContent = '同步供应商';
        }
    } catch(e) {
        statusText.textContent = '同步失败: ' + (e && e.message ? e.message : e);
        btn.disabled = false;
        btn.textContent = '同步供应商';
    }
}

function startSupplierPoll() {
    const btn = document.getElementById('syncBtn');
    const statusText = document.getElementById('syncStatusText');
    const poll = setInterval(async () => {
        try {
            const res = await fetch('/api/sync/status');
            const data = await res.json();
            if (!data.running) {
                clearInterval(poll);
                statusText.textContent = '同步完成！';
                btn.disabled = false;
                btn.textContent = '同步供应商';
                setTimeout(() => {
                    document.getElementById('syncStatus').style.display = 'none';
                    loadData();
                }, 1500);
            }
        } catch(e) {}
    }, 5000);
}'''

content = content.replace(old_sup_sync, new_sup_sync)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('suppliers.html updated')

# ============================================================
# 4. after_sales.html - Fix sync polling
# ============================================================
path = os.path.join(BASE, 'after_sales.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_as_sync = '''async function syncData(type) {
    const res = await apiCall('/api/sync', 'POST', { type });
    alert(res.message);
    if (res.success) location.reload();
}'''

new_as_sync = '''async function syncData(type) {
    if (!confirm('同步需要几分钟时间，后台运行中请勿关闭页面。开始同步？')) return;
    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        if (res.success) {
            alert('同步已将在后台启动');
            startAfterSalesPoll();
        } else {
            alert('同步启动失败: ' + (res.message || '未知错误'));
        }
    } catch(e) {
        alert('请求失败: ' + e.message);
    }
}

function startAfterSalesPoll() {
    const poll = setInterval(async () => {
        try {
            const res = await fetch('/api/sync/status');
            const data = await res.json();
            if (!data.running) {
                clearInterval(poll);
                location.reload();
            }
        } catch(e) {}
    }, 5000);
}'''

content = content.replace(old_as_sync, new_as_sync)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('after_sales.html updated')

# ============================================================
# 5. orders.html - Fix sync polling
# ============================================================
path = os.path.join(BASE, 'orders.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_orders_sync = '''async function syncData(type) {
    const res = await apiCall('/api/sync', 'POST', { type });
    alert(res.message);
    if (res.success) location.reload();
}'''

new_orders_sync = '''async function syncData(type) {
    if (!confirm('同步需要几分钟时间，后台运行中请勿关闭页面。开始同步？')) return;
    try {
        const res = await apiCall('/api/sync', 'POST', { type });
        if (res.success) {
            alert('同步将在后台启动');
            startOrdersSyncPoll();
        } else {
            alert('同步启动失败: ' + (res.message || '未知错误'));
        }
    } catch(e) {
        alert('请求失败: ' + e.message);
    }
}

function startOrdersSyncPoll() {
    const poll = setInterval(async () => {
        try {
            const res = await fetch('/api/sync/status');
            const data = await res.json();
            if (!data.running) {
                clearInterval(poll);
                location.reload();
            }
        } catch(e) {}
    }, 5000);
}'''

content = content.replace(old_orders_sync, new_orders_sync)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('orders.html updated')

print('All frontend sync fixes done!')
