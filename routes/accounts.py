"""
账号管理路由
"""
import logging
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from routes.auth import check_auth, is_auth_enabled

accounts_bp = Blueprint('accounts', __name__)
logger = logging.getLogger(__name__)


@accounts_bp.route('/login')
def login_page():
    next_url = request.args.get('next', '/')
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - 聚水潭数据统计中心</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
    <div style="background:var(--bg-card);border:1px solid var(--border-primary);border-radius:12px;padding:40px;width:100%;max-width:380px;">
        <h2 style="text-align:center;margin-bottom:24px;">⚡ 聚水潭数据统计中心</h2>
        <form method="POST" action="/api/login">
            <input type="hidden" name="next" value="{next_url}">
            <div style="margin-bottom:16px;">
                <label style="display:block;margin-bottom:6px;color:var(--text-muted);">管理员密码</label>
                <input type="password" name="password" required
                    style="width:100%;padding:10px;background:rgba(15,23,42,0.6);border:1px solid var(--border-primary);border-radius:6px;color:var(--text-primary);">
            </div>
            <button type="submit" style="width:100%;padding:12px;background:var(--accent-cyan);color:#000;border:none;border-radius:6px;font-weight:600;cursor:pointer;">
                登录
            </button>
        </form>
        {"<p style='color:var(--accent-red);text-align:center;margin-top:12px;'>密码错误</p>" if request.args.get('error') else ""}
    </div>
</body>
</html>
"""


@accounts_bp.route('/api/login', methods=['POST'])
def api_login():
    password = request.form.get('password', '') or request.json.get('password', '') if request.is_json else ''
    next_url = request.form.get('next', '/') or request.args.get('next', '/')
    
    if check_auth(password):
        session['logged_in'] = True
        return redirect(next_url)
    return redirect(url_for('accounts.login_page', next=next_url, error=1))


@accounts_bp.route('/api/logout')
def api_logout():
    session.pop('logged_in', None)
    return redirect('/')


@accounts_bp.route('/accounts')
def accounts_page():
    from config import ACCOUNTS
    # 只显示账号名，不显示密码
    account_list = []
    for acc in ACCOUNTS:
        account_list.append({
            'name': acc.get('name', acc['username']),
            'username': acc['username'],
            'has_password': bool(acc.get('password')),
        })
    return render_template('accounts.html', accounts=account_list, auth_enabled=is_auth_enabled())


@accounts_bp.route('/api/accounts')
def api_accounts():
    from config import ACCOUNTS
    account_list = []
    for acc in ACCOUNTS:
        account_list.append({
            'name': acc.get('name', acc['username']),
            'username': acc['username'],
        })
    return jsonify({'data': account_list})