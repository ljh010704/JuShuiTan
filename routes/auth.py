"""
登录认证模块 - 简单的 Session 认证
"""
import os
import functools
import logging
from flask import session, redirect, url_for, request, flash

logger = logging.getLogger(__name__)

# 从环境变量读取管理员密码，默认值仅用于开发
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')


def login_required(view):
    """要求登录的装饰器"""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # 如果没有设置密码，跳过认证（开发模式）
        if not ADMIN_PASSWORD:
            return view(**kwargs)
        if not session.get('logged_in'):
            return redirect(url_for('accounts.login_page', next=request.url))
        return view(**kwargs)
    return wrapped_view


def check_auth(password):
    """验证密码"""
    if not ADMIN_PASSWORD:
        # 未设置密码时，任何密码都通过（开发模式）
        return True
    return password == ADMIN_PASSWORD


def is_auth_enabled():
    """检查是否启用了认证"""
    return bool(ADMIN_PASSWORD)