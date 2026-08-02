# 聚水潭数据统计中心

聚水潭供应链平台数据自动化统计系统，基于 Flask + Playwright + SQLite。

## 功能

- **统计看板** — 订单/利润/成本实时统计，支持日期范围筛选（今日/近7天/近30天）
- **数据大屏** — 可视化大屏，支持日期范围筛选
- **订单管理** — 订单查询、筛选、导出 Excel、订单详情、备注编辑
- **售后管理** — 售后单管理、审核同意/拒绝、导出 Excel
- **利润统计** — 分销Plus利润趋势、店铺利润分析
- **利润检测** — 对接聚水潭分销店铺商品利润检测 + 批量下架
- **供应商分析** — 供应商订单统计、合作解除
- **数据同步** — 后台自动/手动同步聚水潭数据，每15分钟定时同步
- **账号管理** — 多账号配置

## 本地运行

```bash
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

访问 http://127.0.0.1:5000

## 服务器部署

Ubuntu 22.04 一键部署：

```bash
bash deploy.sh
```

## 配置

编辑 `.env` 文件（或在 `config.py` 中修改）：

```
ACCOUNT1_NAME=账号名称
ACCOUNT1_USERNAME=手机号
ACCOUNT1_PASSWORD=密码
```

## 技术栈

- Python 3.10+ / Flask
- Playwright（浏览器自动化）
- SQLite
- Chart.js（图表）
