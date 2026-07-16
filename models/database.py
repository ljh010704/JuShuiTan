"""
SQLite 数据库模型与操作
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta


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

    conn.commit()
    conn.close()

    # ????????
    ProfitCheckModel.init_table()


class OrderModel:
    @staticmethod
    def upsert(order):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO orders (account_name, order_id, external_id, shop_id, shop_name, order_type, status,
                    status_desc, item_count, pay_amount, freight, discount_amount,
                    purchase_cost, profit, created_at, paid_at, shipped_at, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    def get_date_range(start_date, end_date):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM orders WHERE created_at BETWEEN ? AND ? ORDER BY created_at DESC",
                (start_date, end_date)
            ).fetchall()
            return [dict(r) for r in rows]
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
                    COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END), 0) as total_cost,
                    COALESCE(SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END), 0) as total_profit,
                    COUNT(CASE WHEN status IN ('待审核', 'WAIT_CHECK') THEN 1 END) as pending_orders,
                    COUNT(CASE WHEN status IN ('已发货', 'SHIPPED') THEN 1 END) as shipped_orders,
                    COUNT(CASE WHEN status IN ('已完成', 'FINISHED') THEN 1 END) as completed_orders,
                    COUNT(CASE WHEN status IN ('已取消', 'CANCELLED') THEN 1 END) as cancelled_orders
                FROM orders WHERE created_at LIKE ?
            """, (f"{date_str}%",)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def count():
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM orders").fetchone()
            return row['cnt'] if row else 0
        finally:
            conn.close()

    @staticmethod
    def get_by_id(order_id):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            return dict(row) if row else None
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


class AfterSalesModel:
    @staticmethod
    def upsert(item):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO after_sales (after_sale_id, order_id, external_id, shop_id, shop_name, type,
                    status, reason, amount, quantity, created_at, processed_at, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(after_sale_id) DO UPDATE SET
                    order_id=excluded.order_id,
                    external_id=excluded.external_id,
                    shop_id=excluded.shop_id,
                    shop_name=excluded.shop_name,
                    type=excluded.type,
                    status=excluded.status,
                    reason=excluded.reason,
                    amount=excluded.amount,
                    quantity=excluded.quantity,
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
    def get_stats_for_date(date_str):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_after_sales,
                    COALESCE(SUM(amount), 0) as refund_amount,
                    COUNT(CASE WHEN type LIKE '%退货%' OR type='RETURN' THEN 1 END) as return_count,
                    COUNT(CASE WHEN type LIKE '%退款%' OR type='REFUND' THEN 1 END) as refund_count,
                    COUNT(CASE WHEN type LIKE '%换货%' OR type='EXCHANGE' THEN 1 END) as exchange_count
                FROM after_sales WHERE created_at LIKE ?
            """, (f"{date_str}%",)).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    @staticmethod
    def count():
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM after_sales").fetchone()
            return row['cnt'] if row else 0
        finally:
            conn.close()

    @staticmethod
    def get_by_id(order_id):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            return dict(row) if row else None
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


class DailyStatsModel:
    @staticmethod
    def upsert(date_str, stats):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO daily_stats (date, total_orders, total_amount, total_cost, total_profit,
                    new_orders, shipped_orders, completed_orders, cancelled_orders,
                    total_after_sales, refund_amount, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_orders=excluded.total_orders,
                    total_amount=excluded.total_amount,
                    total_cost=excluded.total_cost,
                    total_profit=excluded.total_profit,
                    new_orders=excluded.new_orders,
                    shipped_orders=excluded.shipped_orders,
                    completed_orders=excluded.completed_orders,
                    cancelled_orders=excluded.cancelled_orders,
                    total_after_sales=excluded.total_after_sales,
                    refund_amount=excluded.refund_amount,
                    synced_at=excluded.synced_at
            """, (
                date_str,
                stats.get('total_orders', 0),
                stats.get('total_amount', 0),
                stats.get('total_cost', 0),
                stats.get('total_profit', 0),
                stats.get('new_orders', 0),
                stats.get('shipped_orders', 0),
                stats.get('completed_orders', 0),
                stats.get('cancelled_orders', 0),
                stats.get('total_after_sales', 0),
                stats.get('refund_amount', 0),
                datetime.now().isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_recent(days=30):
        conn = get_connection()
        try:
            since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            rows = conn.execute(
                "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date ASC",
                (since,)
            ).fetchall()
            return [dict(r) for r in rows]
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
    """??????"""

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
                except: pass
                try:
                    d['banned_platform'] = json.loads(d.get('banned_platform', '[]'))
                except: pass
                results.append(d)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_latest():
        rows = ProfitCheckModel.get_recent(1)
        return rows[0] if rows else None

# ????????
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
                    """ + col + "=excluded." + col + """,
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
