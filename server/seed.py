import json
import time
import uuid

from .db import get_conn, is_seeded, mark_seeded


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def seed_if_empty() -> None:
    if is_seeded():
        return

    now = int(time.time() * 1000)
    day = 86400000

    def memo(title, content, category, color, project_id, pinned=False, days_ago=1):
        ts = now - day * days_ago
        return (_uid(), title, content, category, color, project_id, int(pinned), ts, ts)

    def link(name, url, icon, sort_order, project_id=None):
        return (_uid(), name, url, icon, project_id, sort_order)

    def checklist(text, sort_order):
        return (_uid(), text, 0, None, sort_order)

    def operation(title, description, steps, tags, project_id):
        return (_uid(), title, description, json.dumps(steps), json.dumps(tags), project_id)

    def snippet(title, language, code, description, tags, project_id):
        return (_uid(), title, language, code, description, json.dumps(tags), project_id)

    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO memos (id, title, content, category, color, project_id, pinned, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                memo("ADMIN 测试环境", "DEV: https://dev-admin.planetart.com\nSTG: https://stg-admin.planetart.com\nPROD: https://admin.planetart.com\n\n测试账号请联系 QA Lead 获取", "env", "blue", 0, True, 1),
                memo("IPS 生产排程检查", "每日检查 IPS 队列积压情况\n- 待处理订单数 < 500\n- 失败重试任务需人工介入\n- 关注 peak season 流量预警", "general", "orange", 99, True, 2),
                memo("STI 支付回归要点", "重点覆盖:\n- PayPal / Credit Card / Apple Pay\n- 优惠券叠加逻辑\n- 国际地址运费计算\n- 移动端结账流程", "bug", "pink", 1, False, 3),
                memo("MCC 机型适配清单", "热门机型: iPhone 15/16 系列, Samsung S24/S25\n测试项:\n- 摄像头开孔位置\n- 侧边按键开孔\n- 图案缩放与裁切边界", "general", "green", 6, False, 4),
                memo("CafePress 多区域差异", "US / UK / AU / CA 站点差异:\n- 货币与税费显示\n- 配送时效文案\n- 本地化支付方式\n- GDPR / CCPA 合规弹窗", "env", "purple", 169, True, 2),
                memo("通用 API 鉴权", "Authorization: Bearer <token>\n\nHeader 必带:\nX-Project-Id: <project_id>\nX-Request-Id: <uuid>\n\nToken 有效期 2h，刷新: POST /api/auth/refresh", "api", "blue", None, True, 5),
                memo("数据库慢查询排查", "1. 检查 explain 执行计划\n2. 确认索引是否命中\n3. 关注 N+1 查询\n4. 大表分页使用 cursor 而非 offset", "db", "green", None, False, 7),
                memo("本周跨项目测试重点", "1. 情人节活动全站回归\n2. 新支付网关灰度验证\n3. MCC BestBuy 渠道联调\n4. CafePress AU 上线冒烟", "general", "yellow", None, False, 0),
            ],
        )

        conn.executemany(
            "INSERT INTO quick_links (id, name, url, icon, project_id, sort_order) VALUES (?,?,?,?,?,?)",
            [
                link("JIRA", "https://planetart.atlassian.net", "🎫", 0),
                link("Confluence", "https://planetart.atlassian.net/wiki", "📚", 1),
                link("TestRail", "https://planetart.testrail.io", "🧪", 2),
                link("Jenkins", "https://jenkins.planetart.com", "🔧", 3),
                link("GitLab", "https://gitlab.planetart.com", "📦", 4),
                link("Kibana", "https://kibana.planetart.com", "📊", 5),
                link("ADMIN", "https://admin.planetart.com", "⚙️", 6, 0),
                link("STI", "https://www.simplytoimpress.com", "💌", 7, 1),
                link("MCC", "https://www.mycustomcase.com", "📱", 8, 6),
            ],
        )

        conn.executemany(
            "INSERT INTO checklist_items (id, text, completed, completed_at, sort_order) VALUES (?,?,?,?,?)",
            [
                checklist("查看 CI 构建状态", 0),
                checklist("检查各项目测试环境健康", 1),
                checklist("Review 当天提交的 MR", 2),
                checklist("跟进 JIRA 高优先级 Bug", 3),
                checklist("更新 TestRail 执行结果", 4),
                checklist("参加每日站会", 5),
            ],
        )

        conn.executemany(
            "INSERT INTO operations (id, title, description, steps, tags, project_id) VALUES (?,?,?,?,?,?)",
            [
                operation("ADMIN 订单状态变更", "通过后台修改订单状态的标准流程", [
                    "登录 ADMIN 后台 (需 admin 权限)",
                    "搜索目标订单号",
                    "进入订单详情 → Actions → Change Status",
                    "选择目标状态并填写变更原因",
                    "确认操作并检查 IPS 队列是否同步",
                    "在 Kibana 验证相关日志无异常",
                ], ["admin", "order", "workflow"], 0),
                operation("STI 新用户注册冒烟", "STI 站点注册流程快速验证", [
                    "访问 www.simplytoimpress.com",
                    "点击 Sign Up 创建新账号",
                    "验证邮箱确认邮件送达",
                    "完成个人信息填写",
                    "添加商品到购物车并进入结账",
                    "使用测试卡完成支付 (4111111111111111)",
                    "确认订单确认页和邮件通知",
                ], ["sti", "smoke", "registration"], 1),
                operation("MCC 手机壳定制流程", "MyCustomCase 完整定制下单流程", [
                    "选择手机型号 (如 iPhone 16 Pro)",
                    "上传自定义图片 / 选择模板",
                    "调整图片位置与缩放",
                    "预览正面/背面效果",
                    "加入购物车并选择配件",
                    "完成结账与支付",
                    "验证生产文件生成 (IPS)",
                ], ["mcc", "customization", "e2e"], 6),
                operation("CafePress 商品上架检查", "新商品上架后的 QA 检查清单", [
                    "确认商品页面图片加载正常",
                    "验证价格与货币符号正确",
                    "测试定制编辑器功能",
                    "检查各尺寸/颜色变体",
                    "验证加入购物车与库存逻辑",
                    "测试多区域站点显示一致性",
                    "确认 SEO meta 信息完整",
                ], ["cafepress", "product", "checklist"], 169),
                operation("生产环境发布流程", "标准生产发布流程 (适用所有项目)", [
                    "确认 CI 全绿 & 代码 Review 完成",
                    "Staging 环境冒烟测试通过",
                    "提交变更审批 (Change Request)",
                    "执行 DB Migration (如有)",
                    "灰度发布: 10% → 50% → 100%",
                    "监控错误率 & 关键业务指标 30min",
                    "通知相关团队发布完成",
                ], ["deploy", "production", "release"], None),
            ],
        )

        conn.executemany(
            "INSERT INTO snippets (id, title, language, code, description, tags, project_id) VALUES (?,?,?,?,?,?,?)",
            [
                snippet("查询项目订单 (MySQL)", "sql",
                    "SELECT o.id, o.status, o.total, o.created_at\nFROM orders o\nWHERE o.project_id = 1\n  AND o.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)\nORDER BY o.created_at DESC\nLIMIT 50;",
                    "按项目 ID 查询近 7 天订单", ["mysql", "orders"], 1),
                snippet("ADMIN API - 获取订单详情", "bash",
                    'curl -s -X GET "https://admin.planetart.com/api/orders/{order_id}" \\\n  -H "Authorization: Bearer $TOKEN" \\\n  -H "X-Project-Id: 0" | jq .',
                    "通过 ADMIN API 查询订单", ["api", "admin", "curl"], 0),
                snippet("MCC 清理测试订单", "sql",
                    'UPDATE orders SET status = "cancelled"\nWHERE project_id = 6\n  AND user_email LIKE "%@planetart-test.com"\n  AND created_at < DATE_SUB(NOW(), INTERVAL 3 DAY);',
                    "清理 MCC 测试账号产生的过期订单", ["mysql", "mcc", "cleanup"], 6),
                snippet("K8s 查看项目 Pod 日志", "bash",
                    "# 按项目标签查看日志\nkubectl logs -l app=sti-web,env=stg --tail=100 -f\n\n# 查看上一个崩溃容器\nkubectl logs deployment/mcc-api --previous --tail=50",
                    "Kubernetes 日志排查常用命令", ["kubernetes", "logs", "debugging"], None),
                snippet("并发压测 API", "bash",
                    '#!/bin/bash\nab -n 1000 -c 50 \\\n  -H "Authorization: Bearer $TOKEN" \\\n  -H "X-Project-Id: $PROJECT_ID" \\\n  -H "Content-Type: application/json" \\\n  "https://api.planetart.com/v1/health"',
                    "Apache Bench 并发压测", ["api", "performance"], None),
                snippet("Git 紧急回滚", "git",
                    "# 创建反向提交 (推荐)\ngit revert HEAD\n\n# 回滚到指定 commit\ngit revert <commit-hash>..HEAD\n\n# 强制推送 (谨慎!)\ngit push --force-with-lease origin <branch>",
                    "生产事故紧急回滚操作", ["git", "rollback", "emergency"], None),
            ],
        )

        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)",
            (json.dumps("light"),),
        )
        conn.commit()

    mark_seeded()
