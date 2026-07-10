"""
账号管理路由
"""
from flask import Blueprint, render_template, jsonify, request

accounts_bp = Blueprint('accounts', __name__)


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
    return render_template('accounts.html', accounts=account_list)


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
