"""
聚水潭数据统计中心 - Flask 主应用
"""
import os
import sys
import logging
import threading

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, session, request, redirect, url_for
from models.database import init_db
from routes.index import index_bp
from routes.orders import orders_bp
from routes.after_sales import after_sales_bp
from routes.sync import sync_bp
from routes.accounts import accounts_bp
from routes.profit import profit_bp
from routes.dashboard import dashboard_bp
from routes.supplier import supplier_bp
from routes.profit_check import profit_check_bp
from routes.auth import is_auth_enabled, ADMIN_PASSWORD

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("jushuitan.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# 定时同步相关
_scheduler = None
_sync_status = {"running": False, "last_sync": None, "next_sync": None}


def auto_sync_job():
    """定时同步任务"""
    import asyncio
    from routes.sync import run_sync_async
    from config import ACCOUNTS, BROWSER

    if _sync_status["running"]:
        logger.info("[定时同步] 上次同步仍在运行，跳过")
        return

    _sync_status["running"] = True
    try:
        logger.info("[定时同步] 开始自动同步...")
        result = run_sync_async("full", {"accounts": ACCOUNTS, "browser": BROWSER})
        _sync_status["last_sync"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = result.get("message", "")
        logger.info(f"[定时同步] 完成: {msg}")
    except Exception as e:
        logger.error(f"[定时同步] 失败: {e}")
    finally:
        _sync_status["running"] = False


def start_scheduler(interval_minutes=15):
    """启动定时任务"""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            auto_sync_job,
            "interval",
            minutes=interval_minutes,
            id="auto_sync",
            replace_existing=True,
        )
        _scheduler.start()
        _sync_status["next_sync"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[定时同步] 已启动，每 {interval_minutes} 分钟同步一次")
    except ImportError:
        logger.warning("[定时同步] 未安装 apscheduler，定时同步不可用")


def create_app():
    app = Flask(__name__)
    # 从环境变量读取 SECRET_KEY，提供随机默认值
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    # 注册路由蓝图
    app.register_blueprint(index_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(after_sales_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(profit_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(profit_check_bp)

    # 初始化数据库
    init_db()

    # 启动定时同步（每15分钟）
    start_scheduler(15)

    # 注入同步状态到模板
    @app.context_processor
    def inject_sync_status():
        return dict(sync_status=_sync_status)

    # 全局认证检查
    @app.before_request
    def require_auth():
        # 不需要认证的路径
        exempt_paths = ["/login", "/api/login", "/api/logout", "/static/"]
        if any(request.path.startswith(p) for p in exempt_paths):
            return None
        # 如果设置了管理员密码，检查登录状态
        if is_auth_enabled() and not session.get("logged_in"):
            return redirect(url_for("accounts.login_page", next=request.url))

    return app


if __name__ == "__main__":
    from config import WEB

    app = create_app()
    # 打印系统内存信息
    try:
        import psutil

        mem = psutil.virtual_memory()
        logger.info(
            f"[系统] 总内存: {mem.total/1024/1024/1024:.1f}GB | 可用: {mem.available/1024/1024/1024:.1f}GB | 使用率: {mem.percent}%"
        )
    except ImportError:
        logger.warning("[系统] 未安装 psutil，跳过内存检测: pip install psutil")
    app.run(
        host=WEB.get("host", "0.0.0.0"),
        port=WEB.get("port", 5000),
        debug=WEB.get("debug", False),
    )