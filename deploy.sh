#!/bin/bash
# ============================================================
# 聚水潭数据统计中心 - 一键部署脚本（Ubuntu 22.04）
# 使用方法：在云服务器上执行 bash deploy.sh
# ============================================================

set -e

APP_NAME="JuShuiTan"
APP_DIR="/home/$APP_NAME"
REPO="https://github.com/ljh010704/JuShuiTan.git"
SERVICE_NAME="jushuitan"

echo "============================================"
echo "  $APP_NAME 一键部署"
echo "============================================"

# --- 1. 系统依赖 ---
echo "[1/7] 安装系统依赖..."
sudo apt update -y
sudo apt install -y \
    python3 python3-pip python3-venv \
    wget unzip curl \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libxshmfence1 libgtk-3-0 \
    --no-install-recommends

# --- 2. 克隆代码 ---
echo "[2/7] 克隆项目..."
if [ -d "$APP_DIR" ]; then
    echo "目录已存在，更新代码..."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO" "$APP_DIR"
fi

cd "$APP_DIR"

# --- 3. Python 虚拟环境 ---
echo "[3/7] 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# --- 4. Python 依赖 ---
echo "[4/7] 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# --- 5. Playwright ---
echo "[5/7] 安装 Playwright 浏览器..."
playwright install chromium
playwright install-deps chromium || sudo apt install -y $(playwright install-deps chromium 2>&1 | grep -oP 'sudo apt install.*' || true)

# --- 6. 配置检查 ---
echo "[6/7] 检查配置..."
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，请编辑 .env 填入聚水潭账号密码："
    echo "   nano $APP_DIR/.env"
    echo ""
    echo "格式示例："
    echo "ACCOUNT1_NAME=账号名"
    echo "ACCOUNT1_USERNAME=手机号"
    echo "ACCOUNT1_PASSWORD=密码"
    echo ""
    read -p "按回车继续..."
fi

if [ ! -f config.py ]; then
    cp config.example.py config.py
fi

# --- 7. 系统服务 ---
echo "[7/7] 配置系统服务..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=JuShuiTan Stats Center
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python app.py
Restart=on-failure
RestartSec=10
Environment=LOW_MEMORY_MODE=true
Environment=AUTO_GC=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo ""
echo "============================================"
echo "  ✅ 部署完成！"
echo "============================================"
echo ""
echo "  访问地址：http://$(curl -s ifconfig.me):5000"
echo ""
echo "  常用命令："
echo "    查看状态：sudo systemctl status $SERVICE_NAME"
echo "    重启服务：sudo systemctl restart $SERVICE_NAME"
echo "    查看日志：sudo journalctl -u $SERVICE_NAME -f"
echo "    改配置：  nano $APP_DIR/.env && sudo systemctl restart $SERVICE_NAME"
echo "    更新代码：cd $APP_DIR && git pull && sudo systemctl restart $SERVICE_NAME"
echo ""
