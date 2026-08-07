"""
SQLite 数据库模型与操作
"""
import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'jushuitan.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT DEFAULT '',
        order_id TEXT UNIQUE,
        external_id TEXT,
        shop_id TEXT,
        shop_name TEXT,
        order_type TEXT DEFAULT '',
        status TEXT,
        status_desc TEXT,
        item_count INTEGER DEFAULT 0,
        pay_amount REAL DEFAULT 0,
        freight REAL DEFAULT 0,
        discount_amount REAL DEFAULT 0,
        purchase_cost REAL DEFAULT 0,
        profit REAL DEFAULT 0,
        created_at TEXT,
        paid_at TEXT,
        shipped_at TEXT,
        synced_at TEXT,
        raw_data TEXT
    );

    CREATE TABLE IF NOT EXISTS after_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        after_sale_id TEXT UNIQUE,
        order_id TEXT,
        external_id TEXT,
        shop_id TEXT,
        shop_name TEXT,
        type TEXT,
        status TEXT,
        reason TEXT,
        amount REAL DEFAULT 0,
        quantity INTEGER DEFAULT 0,
        created_at TEXT,
        processed_at TEXT,
        synced_at TEXT,
        raw_data TEXT
    );

    CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        total_orders INTEGER DEFAULT 0,
        total_amount REAL DEFAULT 0,
        total_cost REAL DEFAULT 0,
        total_profit REAL DEFAULT 0,
        new_orders INTEGER DEFAULT 0,
        shipped_orders INTEGER DEFAULT 0,
        completed_orders INTEGER DEFAULT 0,
        cancelled_orders INTEGER DEFAULT 0,
        total_after_sales INTEGER DEFAULT 0,
        refund_amount REAL DEFAULT 0,
        synced_at TEXT
    );

    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type TEXT,
        status TEXT,
        records_count INTEGER DEFAULT 0,
        error_message TEXT,
        started_at TEXT,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS sync_state (
        account_name TEXT PRIMARY KEY,
        last_order_sync TEXT,
        last_after_sale_sync TEXT,
        total_orders_synced INTEGER DEFAULT 0,
        updated_at TEXT
    );
    """)

    # 售后供应商跟进字段迁移（已有列则跳过）
    after_cols = [r[1] for r in cursor.execute("PRAGMA table_info(after_sales)").fetchall()]
    if 'supplier_status' not in after_cols:
        cursor.execute("ALTER TABLE after_sales ADD COLUMN supplier_status TEXT DEFAULT ''")
    if 'supplier_pushed_at' not in after_cols:
        cursor.execute("ALTER TABLE after_sales ADD COLUMN supplier_pushed_at TEXT")
    if 'note' not in after_cols:
        cursor.execute("ALTER TABLE after_sales ADD COLUMN note TEXT DEFAULT ''")

    # 订单供应商字段迁移 + 从 raw_data 回填历史数据
    order_cols = [r[1] for r in cursor.execute("PRAGMA table_info(orders)").fetchall()]
    if 'supplier_co_id' not in order_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN supplier_co_id TEXT DEFAULT ''")
    if 'supplier_name' not in order_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN supplier_name TEXT DEFAULT ''")
    cursor.execute("""
        UPDATE orders SET
            supplier_co_id = COALESCE(json_extract(raw_data, '$.supplierCoId'), ''),
            supplier_name = COALESCE(json_extract(raw_data, '$.supplierName'), '')
        WHERE (supplier_name IS NULL OR supplier_name = '')
          AND raw_data IS NOT NULL AND raw_data != ''
          AND json_extract(raw_data, '$.supplierName') IS NOT NULL
    """)

    conn.commit()
    conn.close()

    # 初始化利润检测表
    ProfitCheckModel.init_table()


class OrderModel:
    @staticmethod
    def upsert(order):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO orders (account_name, order_id, external_id, shop_id, shop_name, order_type, status,
                    status_desc, item_count, pay_amount, freight, discount_amount,
                    purchase_cost, profit, created_at, paid_at, shipped_at, supplier_co_id, supplier_name, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    account_name=excluded.account_name,
                    external_id=excluded.external_id,
                    shop_id=excluded.shop_id,
                    shop_name=excluded.shop_name,
                    order_type=excluded.order_type,
                    status=excluded.status,
                    status_desc=excluded.status_desc,
                    item_count=excluded.item_count,
                    pay_amount=excluded.pay_amount,
                    freight=excluded.freight,
                    discount_amount=excluded.discount_amount,
                    purchase_cost=excluded.purchase_cost,
                    profit=excluded.profit,
                    created_at=excluded.created_at,
                    paid_at=excluded.paid_at,
                    shipped_at=excluded.shipped_at,
                    supplier_co_id=excluded.supplier_co_id,
                    supplier_name=excluded.supplier_name,
                    synced_at=excluded.synced_at,
                    raw_data=excluded.raw_data
            """, (
                order.get('account_name', ''),
                order.get('order_id', ''),
                order.get('external_id', ''),
                order.get('shop_id', ''),
                order.get('shop_name', ''),
                order.get('order_type', ''),
                order.get('status', ''),
                order.get('status_desc', ''),
                order.get('item_count', 0),
                order.get('pay_amount', 0),
                order.get('freight', 0),
                order.get('discount_amount', 0),
                order.get('purchase_cost', 0),
                order.get('profit', 0),
                order.get('created_at', ''),
                order.get('paid_at', ''),
                order.get('shipped_at', ''),
                order.get('supplier_co_id', ''),
                order.get('supplier_name', ''),
                datetime.now().isoformat(),
                order.get('raw_data', ''),
            ))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_by_date(date_str):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM orders WHERE created_at LIKE ? ORDER BY created_at DESC",
                (f"{date_str}%",)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_range(start_date, end_date, page=1, per_page=50):
        conn = get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM orders WHERE substr(created_at,1,10) BETWEEN ? AND ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (start_date, end_date, per_page, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_all(page=1, per_page=50):
        conn = get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(order_id):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM orders WHERE order_id=? OR external_id=?",
                (order_id, order_id)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def count():
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    @staticmethod
    def get_stats_for_date(date_str):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(pay_amount), 0) as total_amount,
                    COALESCE(SUM(purchase_cost), 0) as total_cost,
                    COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit
                FROM orders WHERE created_at LIKE ?
                  AND status IN ('Sent', 'WaitOuterSent')
                  AND order_type LIKE '%分销Plus%'
                  AND order_type NOT LIKE '%供销%'
                  AND order_type NOT LIKE '%自发%'
            """, (f"{date_str}%",)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def get_stats_for_range(start_date, end_date):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(pay_amount), 0) as total_amount,
                    COALESCE(SUM(purchase_cost), 0) as total_cost,
                    COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit
                FROM orders WHERE substr(created_at,1,10) BETWEEN ? AND ?
                  AND status IN ('Sent', 'WaitOuterSent')
                  AND order_type LIKE '%分销Plus%'
                  AND order_type NOT LIKE '%供销%'
                  AND order_type NOT LIKE '%自发%'
            """, (start_date, end_date)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()


class AfterSalesModel:
    @staticmethod
    def upsert(item):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO after_sales (after_sale_id, order_id, external_id, shop_id, shop_name,
                    type, status, reason, amount, quantity, created_at, processed_at, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(after_sale_id) DO UPDATE SET
                    status=excluded.status,
                    processed_at=excluded.processed_at,
                    synced_at=excluded.synced_at,
                    raw_data=excluded.raw_data
            """, (
                item.get('after_sale_id', ''),
                item.get('order_id', ''),
                item.get('external_id', ''),
                item.get('shop_id', ''),
                item.get('shop_name', ''),
                item.get('type', ''),
                item.get('status', ''),
                item.get('reason', ''),
                item.get('amount', 0),
                item.get('quantity', 0),
                item.get('created_at', ''),
                item.get('processed_at', ''),
                datetime.now().isoformat(),
                item.get('raw_data', ''),
            ))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_by_date(date_str):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM after_sales WHERE created_at LIKE ? ORDER BY created_at DESC",
                (f"{date_str}%",)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_range(start_date, end_date, page=1, per_page=50):
        conn = get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM after_sales WHERE substr(created_at,1,10) BETWEEN ? AND ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (start_date, end_date, per_page, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_all(page=1, per_page=50):
        conn = get_connection()
        try:
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM after_sales ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def count():
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) FROM after_sales").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    @staticmethod
    def get_stats_for_date(date_str):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(amount), 0) as refund_amount
                FROM after_sales WHERE created_at LIKE ?
            """, (f"{date_str}%",)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def get_stats_for_range(start_date, end_date):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(amount), 0) as refund_amount
                FROM after_sales WHERE substr(created_at,1,10) BETWEEN ? AND ?
            """, (start_date, end_date)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def set_supplier_status(after_sale_id, status):
        """更新供应商跟进状态: ''(未推送) / pushed(已推送) / refunded(货款已回)"""
        conn = get_connection()
        try:
            if status == 'pushed':
                conn.execute(
                    "UPDATE after_sales SET supplier_status=?, supplier_pushed_at=? WHERE after_sale_id=?",
                    (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), after_sale_id)
                )
            elif status == '':
                conn.execute(
                    "UPDATE after_sales SET supplier_status=?, supplier_pushed_at='' WHERE after_sale_id=?",
                    (status, after_sale_id)
                )
            else:
                conn.execute(
                    "UPDATE after_sales SET supplier_status=? WHERE after_sale_id=?",
                    (status, after_sale_id)
                )
            conn.commit()
            return True
        finally:
            conn.close()


class DailyStatsModel:
    @staticmethod
    def get_recent(days=30):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?",
                (days,)
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()

    @staticmethod
    def get_for_date(date_str):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM daily_stats WHERE date = ?", (date_str,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class ProfitCheckModel:
    """利润检测数据模型"""

    @staticmethod
    def init_table():
        conn = get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profit_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT DEFAULT '',
                supplier_removed_count INTEGER DEFAULT 0,
                banned_platform_count INTEGER DEFAULT 0,
                supplier_removed TEXT DEFAULT '[]',
                banned_platform TEXT DEFAULT '[]',
                raw_data TEXT DEFAULT '{}',
                checked_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def save(result):
        import json
        conn = get_connection()
        conn.execute("""
            INSERT INTO profit_checks 
                (account_name, supplier_removed_count, banned_platform_count,
                 supplier_removed, banned_platform, raw_data, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result.get('account_name', ''),
            result.get('supplier_removed_count', 0),
            result.get('banned_platform_count', 0),
            json.dumps(result.get('supplier_removed', []), ensure_ascii=False),
            json.dumps(result.get('banned_platform', []), ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            result.get('checked_at', '')
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def get_recent(limit=20):
        import json
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM profit_checks ORDER BY id DESC LIMIT ?", 
                (limit,)
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d['supplier_removed'] = json.loads(d.get('supplier_removed', '[]'))
                except Exception:
                    pass
                try:
                    d['banned_platform'] = json.loads(d.get('banned_platform', '[]'))
                except Exception:
                    pass
                results.append(d)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_latest():
        rows = ProfitCheckModel.get_recent(1)
        return rows[0] if rows else None


# 初始化利润检测表（模块加载时调用）
ProfitCheckModel.init_table()


class SyncLogModel:
    @staticmethod
    def create(sync_type):
        conn = get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO sync_logs (sync_type, status, started_at) VALUES (?, 'running', ?)",
                (sync_type, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(log_id, status, records_count=0, error_message=''):
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE sync_logs SET status=?, records_count=?, error_message=?, finished_at=? WHERE id=?",
                (status, records_count, error_message, datetime.now().isoformat(), log_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_recent(limit=20):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM sync_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class SyncStateModel:
    @staticmethod
    def get_last_sync(account_name, sync_type='orders'):
        """获取账号的最后同步时间"""
        conn = get_connection()
        try:
            col = 'last_order_sync' if sync_type == 'orders' else 'last_after_sale_sync'
            row = conn.execute(
                f"SELECT {col} FROM sync_state WHERE account_name=?",
                (account_name,)
            ).fetchone()
            return row[0] if row and row[0] else None
        finally:
            conn.close()

    @staticmethod
    def update_sync(account_name, sync_type='orders', count=0):
        """更新同步状态"""
        conn = get_connection()
        try:
            col = 'last_order_sync' if sync_type == 'orders' else 'last_after_sale_sync'
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO sync_state (account_name, last_order_sync, last_after_sale_sync, total_orders_synced, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_name) DO UPDATE SET
                    """ + col + """=excluded.""" + col + """,
                    total_orders_synced = sync_state.total_orders_synced + excluded.total_orders_synced,
                    updated_at = excluded.updated_at
            """, (account_name, now if sync_type == 'orders' else None,
                  now if sync_type == 'after_sales' else None, count, now))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_all():
        """获取所有同步状态"""
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM sync_state").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()