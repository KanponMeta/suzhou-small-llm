#!/bin/bash
# suzhou-small-llm Kong服务注册脚本
# 将本服务注册到 pma-network 上的共享 Kong 网关
# Kong 通过容器名 suzhou-small-llm 访问内部端口 8000

set -e

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://localhost:8999}"
SERVICE_NAME="suzhou-small-llm"
SERVICE_URL="http://suzhou-small-llm:8000"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }

check_kong() {
    log_info "检查 Kong 状态..."
    local retries=10
    local count=0
    while [ $count -lt $retries ]; do
        if curl -s "$KONG_ADMIN_URL/status" > /dev/null 2>&1; then
            log_success "Kong 已就绪"
            return 0
        fi
        count=$((count + 1))
        echo -n "."
        sleep 2
    done
    log_error "Kong 未运行或无法访问: $KONG_ADMIN_URL"
    return 1
}

setup() {
    check_kong

    log_info "注册服务: $SERVICE_NAME -> $SERVICE_URL"
    curl -s -X PUT "$KONG_ADMIN_URL/services/$SERVICE_NAME" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "'"$SERVICE_NAME"'",
            "url": "'"$SERVICE_URL"'",
            "connect_timeout": 60000,
            "read_timeout": 300000,
            "write_timeout": 300000,
            "retries": 3
        }' > /dev/null
    log_success "服务已注册"

    log_info "注册路由: /llm -> $SERVICE_NAME"
    curl -s -X PUT "$KONG_ADMIN_URL/routes/$SERVICE_NAME-route" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "'"$SERVICE_NAME"'-route",
            "service": {"name": "'"$SERVICE_NAME"'"},
            "paths": ["/llm"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "strip_path": false,
            "preserve_host": true,
            "protocols": ["http", "https"]
        }' > /dev/null
    log_success "路由已注册"

    log_success "suzhou-small-llm Kong 配置完成"
    echo
    echo "服务地址（Kong内部）: $SERVICE_URL"
    echo "对外路由路径:         /llm"
}

clean() {
    check_kong
    log_info "删除路由和服务..."
    curl -s -X DELETE "$KONG_ADMIN_URL/routes/$SERVICE_NAME-route" > /dev/null 2>&1 || true
    curl -s -X DELETE "$KONG_ADMIN_URL/services/$SERVICE_NAME" > /dev/null 2>&1 || true
    log_success "已清理"
}

case "${1:-setup}" in
    setup) setup ;;
    clean) clean ;;
    *) echo "用法: $0 [setup|clean]" ; exit 1 ;;
esac
