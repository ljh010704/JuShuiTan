"""
利润检测路由 - 分销店铺商品利润检测
"""
import asyncio
import json
import logging
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
from models.database import ProfitCheckModel
from routes.sync import get_browser_session
from browser.profit_check import ProfitCheckScraper

profit_check_bp = Blueprint('profit_check', __name__)
logger = logging.getLogger(__name__)


@profit_check_bp.route('/profit-check')
def profit_check_page():
    latest = ProfitCheckModel.get_latest()
    history = ProfitCheckModel.get_recent(20)
    return render_template('profit_check.html', latest=latest, history=history)


@profit_check_bp.route('/api/profit-check/run', methods=['POST'])
def api_run_profit_check():
    """执行利润检测"""
    session = get_browser_session()
    if not session:
        return jsonify({
            'success': False,
            'message': '浏览器未登录，请先执行一次数据同步'
        })

    try:
        scraper = ProfitCheckScraper(session)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(scraper.fetch_profit_check())
        finally:
            loop.close()

        # 保存到数据库
        result['account_name'] = getattr(session, 'account_name', '未知')
        ProfitCheckModel.save(result)

        return jsonify({
            'success': True,
            'data': result,
            'message': '检测完成'
        })
    except Exception as e:
        logger.error(f"利润检测失败: {e}")
        return jsonify({
            'success': False,
            'message': f'检测失败: {str(e)}'
        })


@profit_check_bp.route('/api/profit-check/latest')
def api_latest_check():
    """获取最近一次检测结果"""
    latest = ProfitCheckModel.get_latest()
    if latest:
        return jsonify({'success': True, 'data': latest})
    return jsonify({'success': False, 'message': '暂无检测记录'})


@profit_check_bp.route('/api/profit-check/history')
def api_check_history():
    """获取检测历史"""
    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20
    history = ProfitCheckModel.get_recent(limit)
    return jsonify({'success': True, 'data': history})


@profit_check_bp.route('/api/profit-check/batch-remove', methods=['POST'])
def api_batch_remove():
    """批量下架商品"""
    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '浏览器未登录，请先执行一次数据同步'})

    data = request.get_json() or {}
    remove_type = data.get('type', 'all')

    try:
        scraper = ProfitCheckScraper(session)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(scraper.batch_remove_products(remove_type))
        finally:
            loop.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"批量下架失败: {e}")
        return jsonify({'success': False, 'message': f'批量下架失败: {str(e)}'})