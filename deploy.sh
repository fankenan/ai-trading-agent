#!/bin/bash
# AI量化Agent - 云服务器部署脚本
# 支持 Ubuntu/CentOS/Debian

set -e

echo "========================================"
echo "  AI量化Agent - 云服务器部署脚本"
echo "========================================"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo -e "${RED}无法检测操作系统${NC}"
    exit 1
fi

echo -e "${GREEN}检测到操作系统: $OS${NC}"

# 安装Docker
install_docker() {
    echo -e "${YELLOW}正在安装 Docker...${NC}"
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        systemctl start docker
        systemctl enable docker
    fi
    
    echo -e "${GREEN}Docker 安装完成${NC}"
}

# 检查Docker
if ! command -v docker &> /dev/null; then
    install_docker
else
    echo -e "${GREEN}Docker 已安装${NC}"
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}安装 Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo -e "${GREEN}Docker Compose 已就绪${NC}"

# 创建工作目录
WORK_DIR="/opt/ai-trading-agent"
echo -e "${YELLOW}创建工作目录: $WORK_DIR${NC}"
mkdir -p $WORK_DIR
cd $WORK_DIR

# 检查必要的文件
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 未找到 docker-compose.yml${NC}"
    echo "请确保已将项目文件上传到服务器"
    exit 1
fi

# 创建环境变量文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}创建 .env 配置文件...${NC}"
    cat > .env << EOF
# Tushare Token (可选，用于切换数据源)
TUSHARE_TOKEN=your_tushare_token_here

# 密钥
SECRET_KEY=$(openssl rand -hex 32)
EOF
    echo -e "${YELLOW}请编辑 .env 文件，填入您的 Tushare Token${NC}"
fi

# 创建日志目录
mkdir -p logs

# 拉取并启动服务
echo -e "${YELLOW}正在构建和启动服务...${NC}"
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

# 等待服务启动
sleep 10

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"
if curl -s http://localhost:5002/api/status > /dev/null; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "访问地址:"
    echo "  - 本地: http://localhost:5002"
    echo "  - 公网: http://$(curl -s ifconfig.me 2>/dev/null || echo '您的服务器IP'):5002"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker logs -f ai-trading-agent"
    echo "  停止服务: docker compose down"
    echo "  重启服务: docker compose restart"
    echo ""
    echo -e "${YELLOW}注意: 如果无法访问，请检查服务器安全组/防火墙是否开放5002端口${NC}"
else
    echo -e "${RED}服务启动可能有问题，请检查日志: docker logs ai-trading-agent${NC}"
    exit 1
fi
