# AI量化Agent - 云服务器部署指南

## 快速部署（推荐）

### 1. 准备服务器

**推荐配置：**
- 阿里云/腾讯云 ECS 或轻量应用服务器
- 配置：2核4G 或更高
- 系统：Ubuntu 20.04/22.04 LTS 或 CentOS 8
- 带宽：3Mbps 或更高

**开放端口：**
- 5002（应用端口）
- 80/443（可选，用于Nginx）

### 2. 上传代码

```bash
# 在本地打包项目
cd ai-trading-agent
tar czvf ai-trading-agent.tar.gz .

# 上传到服务器（使用scp或ftp）
scp ai-trading-agent.tar.gz root@your-server-ip:/opt/

# 在服务器上解压
ssh root@your-server-ip
cd /opt
mkdir -p ai-trading-agent
tar xzvf ai-trading-agent.tar.gz -C ai-trading-agent/
cd ai-trading-agent
```

### 3. 运行部署脚本

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

脚本会自动：
- 安装 Docker 和 Docker Compose
- 构建应用镜像
- 启动服务
- 检查健康状态

### 4. 配置 Tushare Token（可选）

```bash
# 编辑配置文件
nano /opt/ai-trading-agent/.env

# 填入您的 Tushare Token
TUSHARE_TOKEN=your_token_here

# 重启服务
docker compose restart
```

### 5. 访问系统

```
http://your-server-ip:5002
```

---

## 手动部署

如果不使用 Docker，可以手动部署：

### 安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip nodejs npm

# 安装Python依赖
pip3 install -r requirements.txt

# 构建前端
cd web-react
npm install
npm run build
cd ..
```

### 启动服务

```bash
# 使用screen或tmux保持运行
screen -S trading
python3 run_multi_source.py --host 0.0.0.0 --port 5002
```

---

## 配置 HTTPS（推荐）

### 使用 Nginx + Let's Encrypt

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 配置域名

1. 在域名服务商添加 A 记录指向服务器IP
2. 修改 `nginx.conf` 中的 `server_name`
3. 取消 HTTPS 配置的注释
4. 重启服务：`docker compose restart nginx`

---

## 运维管理

### 查看日志

```bash
# 应用日志
docker logs -f ai-trading-agent

# Nginx日志
docker logs -f ai-trading-nginx
```

### 更新部署

```bash
cd /opt/ai-trading-agent

# 拉取最新代码
git pull  # 如果使用git

# 或者重新上传代码后

# 重新构建并启动
docker compose down
docker compose up -d --build
```

### 备份数据

```bash
# 备份配置
cp .env .env.backup

# 备份日志
tar czvf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### 监控服务

```bash
# 查看容器状态
docker ps

# 查看资源使用
docker stats

# 系统监控
curl http://localhost:5002/api/status
```

---

## 常见问题

### Q1: 无法访问服务？

检查防火墙/安全组：
```bash
# 查看端口监听
netstat -tlnp | grep 5002

# 检查防火墙
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-ports  # CentOS
```

### Q2: AKShare无法连接？

可能是网络问题，切换到 Tushare：
```bash
curl -X POST http://localhost:5002/api/datasource \
  -H "Content-Type: application/json" \
  -d '{"source":"tushare"}'
```

### Q3: 如何设置开机自启？

```bash
# Docker 服务已默认开机自启
# 容器也已设置 restart: unless-stopped

# 手动设置
docker update --restart unless-stopped ai-trading-agent
```

---

## 安全建议

1. **修改默认密钥**：编辑 `.env` 文件中的 `SECRET_KEY`
2. **配置防火墙**：仅开放必要的端口
3. **使用HTTPS**：生产环境务必配置SSL证书
4. **定期更新**：及时更新系统和依赖包
5. **监控告警**：配置服务异常告警

---

## 技术支持

如有问题，请检查：
1. 服务日志：`docker logs ai-trading-agent`
2. 系统资源：`free -h` / `df -h`
3. 网络连接：`curl -v http://localhost:5002/api/status`
