# 快乐猴选址系统 — 项目说明文档

> **版本**：v1.0 · 2026-04-16  
> **项目路径**：`~/Desktop/美团商赛/happy_monkey`  
> **在线地址**：http://43.133.46.51:5001

---

## 目录

1. [项目背景与目标](#一项目背景与目标)
2. [整体功能概览](#二整体功能概览)
3. [系统技术架构](#三系统技术架构)
4. [核心技术栈](#四核心技术栈)
5. [三阶段优化模型说明](#五三阶段优化模型说明)
6. [城市参数配置](#六城市参数配置)
7. [RDC 硬约束筛选条件](#七rdc-硬约束筛选条件)
8. [系统 API 接口列表](#八系统-api-接口列表)
9. [输入数据格式规范](#九输入数据格式规范)
10. [前端模块功能说明](#十前端模块功能说明)
11. [AI 对话模块架构](#十一ai-对话模块架构)
12. [部署架构说明](#十二部署架构说明)

---

## 一、项目背景与目标

### 1.1 业务背景

**快乐猴（Happy Monkey）** 是一家专注于社区超市赛道的连锁品牌，正处于多城市规模化扩张阶段。在同时推进 **北京** 和 **杭州** 两地网络布局时，面临以下核心决策问题：

1. **新店候选点筛选**：如何从大量候选地址中，识别出财务可行的开店位置？
2. **新店蚕食效应控制**：相邻新店之间会互相分流客流，如何在最大化整体收益的同时，避免严重的内部竞争？
3. **区域配送中心（RDC）选址**：要支撑门店网络的正常运营，需要在城市内建立 RDC 提供冷链配送。如何选择 RDC 数量和位置，使全网物流成本最低？

### 1.2 项目目标

本项目基于美团商赛课题要求，参考以下内部文档实现端到端的选址决策系统：

- 《快乐猴 RDC 候选点生成全流程》
- 《快乐猴社区超市联合选址优化模型》
- 《快乐猴选址展示前端系统设计方案》

**系统目标**：提供一套基于网页的交互式决策工具，让业务同学上传门店/RDC 候选点数据后，即可一键运行三阶段优化模型，并在地图上直观查看推荐结果、成本分析和 RDC 网络规划。

### 1.3 项目亮点

| 亮点 | 说明 |
|------|------|
| 三阶段联合优化 | Stage 2（蚕食）与 Stage 3（RDC 选址）联合求解，消除分段决策偏差 |
| 纯 Python 实现 | 无需外部求解器（Gurobi/CPLEX），组合枚举 + 束搜索，开箱可用 |
| 实时 AI 对话 | 集成 OpenClaw 智能代理（底层 DeepSeek 模型），支持 SSE 流式逐字输出 |
| GIS 可视化 | Leaflet.js 三阶段地图时间轴，含通行禁区、物流带、RDC-门店连线 |
| 自定义 RDC | 支持在地图上点击添加自定义 RDC 候选点，实时校验禁区合规性 |

---

## 二、整体功能概览

```
┌─────────────────────────────────────────────────────────────┐
│                     快乐猴选址系统                           │
│                                                             │
│  ┌─────────────────────────┐  ┌──────────────────────────┐ │
│  │    选址优化分析模块       │  │      AI 智能对话模块      │ │
│  │                         │  │                          │ │
│  │ • 上传 CSV 或用样例数据   │  │ • 对话历史管理            │ │
│  │ • 城市 / 参数配置         │  │ • 多会话上下文保持         │ │
│  │ • 一键运行三阶段模型       │  │ • SSE 流式逐字渲染        │ │
│  │ • 结果看板 + 情景对比      │  │ • 复用 session，保留记忆  │ │
│  │ • GIS 三阶段地图可视化     │  │                          │ │
│  └─────────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**三阶段优化模型流程**：

```
输入数据
  stores.csv（门店候选点）
  rdcs.csv（RDC 候选点）
  distances.csv（可选，距离矩阵）
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │ Stage 1：单点财务筛选                         │
  │   计算每个候选门店的 5 年 NPV、DPP、坪效       │
  │   应用硬指标闸门 → 输出通过/未通过结果          │
  └─────────────────────┬───────────────────────┘
                        │ 筛选通过的候选点
                        ▼
  ┌─────────────────────────────────────────────┐
  │ Stage 2：新店蚕食优化                         │
  │   计算候选点两两距离，<300m 硬冲突，300-500m   │
  │   衰减惩罚；枚举组合，最大化调整后总 NPV        │
  └─────────────────────┬───────────────────────┘
                        │ 最优新店选址方案
                        ▼
  ┌─────────────────────────────────────────────┐
  │ Stage 3：RDC + 门店联合选址（P-median）       │
  │   筛选合规 RDC 候选点（8 项硬约束）            │
  │   枚举 P=1,2,3…个 RDC 的组合方案              │
  │   为每个方案分配门店，最小化全网总成本          │
  └─────────────────────┬───────────────────────┘
                        │
                        ▼
                  最优选址方案输出
         （地图可视化 + 成本分析 + 情景对比）
```

---

## 三、系统技术架构

### 3.1 系统架构总图

```
═══════════════════════════════════════════════════════════════════
                         系统技术架构图
═══════════════════════════════════════════════════════════════════

  【用户终端层】
  ┌───────────────────────────────────────────────────────────┐
  │               浏览器（Chrome / Safari 等）                  │
  │                                                           │
  │   ┌──────────────────────────┐  ┌─────────────────────┐  │
  │   │      选址分析前端         │  │     AI 对话前端      │  │
  │   │  HTML + CSS + Vanilla JS │  │  fetch + ReadableStream│ │
  │   │  Leaflet.js（GIS 地图）  │  │  SSE 帧解析 + 逐字渲染│  │
  │   └──────────────┬───────────┘  └──────────┬──────────┘  │
  └─────────────────-│──────────────────────────│─────────────┘
                     │ HTTP / JSON              │ SSE 流
                     │                          │ text/event-stream
  ═══════════════════│══════════════════════════│═══════════════
  【应用服务层】      │ 腾讯云 CVM               │ 43.133.46.51:5001
  ┌──────────────────┼──────────────────────────┼─────────────┐
  │                  ▼                          ▼             │
  │  ┌──────────────────────────────────────────────────────┐ │
  │  │                 Flask Web Server (app.py)             │ │
  │  │                                                      │ │
  │  │  GET  /                    ← 返回前端 HTML 页面        │ │
  │  │  GET  /api/cities          ← 城市 GIS 元数据           │ │
  │  │  POST /api/run             ← 上传 CSV 运行优化          │ │
  │  │  POST /api/run-sample      ← 使用内置样例数据            │ │
  │  │  POST /api/validate-rdc-point ← 验证禁区合规           │ │
  │  │  POST /api/chat/stream     ← AI 对话（SSE 主用）        │ │
  │  │  POST /api/chat            ← AI 对话（阻塞降级备用）      │ │
  │  └──────────┬───────────────────────────┬───────────────┘ │
  │             │                           │                 │
  │             ▼                           ▼                 │
  │  ┌──────────────────────┐   ┌────────────────────────┐   │
  │  │   optimizer.py        │   │  openclaw_client.py     │   │
  │  │   （核心优化引擎）      │   │  （AI 通信客户端）        │   │
  │  │                      │   │                        │   │
  │  │  Stage 1 财务筛选     │   │  WebSocket 连接管理     │   │
  │  │  Stage 2 蚕食优化     │   │  queue.Queue 跨线程桥   │   │
  │  │  Stage 3 P-median    │   │  Generator 流式 yield   │   │
  │  │  haversine 距离计算   │   │  Session 复用逻辑        │   │
  │  │  RDC 硬约束筛选       │   └───────────┬────────────┘   │
  │  │  束搜索剪枝加速        │               │ WebSocket       │
  │  └──────────┬───────────┘               │ ws://127.0.0.1  │
  │             │                           │    :18789        │
  │             ▼                           ▼                 │
  │  ┌──────────────────────┐   ┌────────────────────────┐   │
  │  │   sample_data/        │   │   OpenClaw 本地 Agent   │   │
  │  │   stores.csv          │   │   （同机部署，本机回环）  │   │
  │  │   rdcs.csv            │   │   底层模型：DeepSeek    │   │
  │  │   distances.csv       │   │   协议：WebSocket v3    │   │
  │  └──────────┬───────────┘   └────────────────────────┘   │
  │             │                                             │
  │             ▼（可选）                                      │
  │  ┌──────────────────────┐                                 │
  │  │   高德地图距离 API     │                                 │
  │  │ restapi.amap.com      │                                 │
  │  │ /v3/distance          │                                 │
  │  │ 真实路网驾车距离       │                                 │
  │  └──────────────────────┘                                 │
  └────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════
  【部署与运维层】
  ┌────────────────────────────────────────────────────────────┐
  │                                                            │
  │  本地 Mac 开发机                  腾讯云 CVM 服务器          │
  │  ~/Desktop/美团商赛/happy_monkey  43.133.46.51             │
  │            │                              │               │
  │            │  git push (SSH + PEM 密钥)   │               │
  │            └──────────────────────────►  │               │
  │                                    ~/happymonkey-site.git │
  │                                    （裸仓库 / Git 远端）   │
  │                                          │ git pull       │
  │                                          ▼               │
  │                                    ~/happymonkey-site/    │
  │                                    （工作目录）            │
  │                                          │               │
  │                                    start.sh 注入环境变量   │
  │                                    nohup python3 app.py   │
  │                                    0.0.0.0:5001 监听      │
  │                                                           │
  │  一键部署脚本：./deploy.sh "提交信息"                        │
  │  （git add → commit → push → 服务器 pull → 重启 Flask）     │
  └────────────────────────────────────────────────────────────┘
```

### 3.2 数据流说明

#### 选址优化流（同步 JSON）

```
浏览器
  │ POST /api/run（multipart/form-data）
  │ 携带：store_file / rdc_file / distance_file (CSV)
  │       + 城市、P值、阈值等参数
  ▼
Flask app.py
  │ 解析 CSV → store_rows / rdc_rows / distance_rows
  │ 可选：调用高德 API 生成真实路网距离矩阵
  ▼
optimizer.py :: run_full_model()
  │ Stage 1 → evaluate_stage1() → NPV / DPP / 坪效
  │ Stage 2+3 → optimize_stage2_stage3_joint()
  │           → 枚举 / 束搜索 + P-median
  ▼
返回 JSON（summary + stage1 + stage2 + stage3 + gis 数据）
  ▼
浏览器前端渲染
  → 汇总看板 / 成本柱状图 / 情景对比卡片
  → Leaflet.js 地图（三阶段图层）
```

#### AI 对话流（SSE 流式）

```
浏览器
  │ POST /api/chat/stream（JSON：messages + session_key）
  │ 使用 fetch + res.body.getReader() 读取流
  ▼
Flask app.py :: chat_stream()
  │ 从 openclaw_chat_stream() 获取事件 generator
  │ 将每个事件序列化为 SSE 帧：data: {...}\n\n
  ▼
openclaw_client.py :: openclaw_chat_stream()
  │ 在独立线程中运行 WebSocket 连接
  │ WebSocket → ws://127.0.0.1:18789（OpenClaw 本机监听）
  │ 握手协议：challenge → connect → create/reuse session
  │         → subscribe → send message → 等待 agent 事件
  │ agent.stream=assistant 事件 → 累积文本 → 放入 Queue
  │ 主线程从 Queue 读取 → yield delta/done/error 事件
  ▼
浏览器
  │ 收到 {"type":"session"} → 保存 session_key
  │ 收到 {"type":"delta","text":"..."} → 更新文本框（累积全文）
  │ 收到 {"type":"done"} → 标记完成
```

---

## 四、核心技术栈

| 层次 | 技术/框架 | 版本要求 | 用途 |
|------|-----------|----------|------|
| 后端语言 | Python | 3.12 | 主语言 |
| Web 框架 | Flask | ≥ 3.0.0 | HTTP 路由、JSON API、SSE 响应 |
| AI 通信 | websocket-client | ≥ 1.6.0 | WebSocket 连接 OpenClaw |
| AI 模型 | OpenClaw / DeepSeek | — | 智能对话代理 |
| 地图库 | Leaflet.js | CDN | GIS 可视化、图层管理 |
| 前端语言 | Vanilla JS + HTML/CSS | — | UI 交互、SSE 解析 |
| 外部 API（可选） | 高德地图距离 API | v3 | 真实路网驾车距离 |
| 部署平台 | 腾讯云 CVM | Ubuntu | 云服务器 |
| 代码管理 | Git（裸仓库部署） | — | 本地 → 服务器代码同步 |
| 运行方式 | nohup + start.sh | — | 后台常驻进程 |

**优化算法说明**（无外部依赖，纯 Python 实现）：

| 算法 | 文件位置 | 说明 |
|------|----------|------|
| NPV / DPP 财务模型 | `optimizer.py:367` | 5 年折现现金流，线性插值 DPP |
| 距离衰减函数 | `optimizer.py:459` | 分段线性，280m / 320m / 500m 三区间 |
| 组合枚举（Stage 2） | `optimizer.py:1101` | 精确枚举，超出阈值时切换束搜索 |
| 束搜索（Stage 2） | `optimizer.py:1126` | Beam Search，保留 top-K 候选 |
| P-median 优化（Stage 3） | `optimizer.py:1366` | 枚举 RDC 组合 + 贪心门店分配 |
| Haversine 球面距离 | `optimizer.py:250` | 经纬度直线距离，降级备用 |

---

## 五、三阶段优化模型说明

### 5.1 Stage 1 — 单点财务筛选

**目的**：对每个新门店候选点独立计算财务指标，过滤掉明显不可行的点位。

**核心公式**：

```
年收入      = rf_sales_10k × 成长因子[year]
毛利润      = 年收入 × gross_margin
运营利润    = 毛利润 − 变动成本 − 年固定成本
税后现金流  = 运营利润 − max(0, 运营利润) × tax_rate
（最后一年加上：初始投资 × 残值率）

NPV = −初始投资 + Σ(年现金流 / (1+折现率)^t)

DPP（折现回收期）= 折现现金流累计首次转正的年份（线性插值）

坪效 = rf_sales_10k / 面积(㎡)
```

**通过条件（三项同时满足）**：

| 指标 | 北京 | 杭州 | 默认 |
|------|------|------|------|
| NPV ≥ | 25 万元 | 28 万元 | 30 万元 |
| DPP ≤ | 2.5 年 | 2.5 年 | 2.5 年 |
| 坪效 ≥ | 1.2 万/㎡ | 1.2 万/㎡ | 1.2 万/㎡ |

> 既有门店（`is_existing=1`）跳过 Stage 1，直接进入 Stage 3 网络。

### 5.2 Stage 2 — 新店蚕食优化

**目的**：从 Stage 1 通过的候选点中，选出一批最优组合，避免相邻门店互相分流。

**距离衰减规则**：

```
d < 280m         → 衰减系数 = 1.0（硬冲突，不可同开）
280m ≤ d < 320m  → 线性衰减 1.0 → 0.35（过渡区）
320m ≤ d < 500m  → 线性衰减 0.35 → 0.0（软惩罚区）
d ≥ 500m         → 衰减系数 = 0.0（无竞争关系）
```

**优化目标**：

```
最大化 Σ 调整后 NPV(选中门店组合)

其中：对于门店 i，若与已选门店 j 存在竞争，
  调整后销售额 = 原始销售额 × (1 − 最大衰减系数)
  调整后 NPV 用调整后销售额重新计算
```

**搜索策略**：
- 候选点较少时：精确枚举所有 C(n, k) 组合
- 候选点较多时：切换为**束搜索（Beam Search）**，保留得分最高的 top-K 候选集合，避免指数级爆炸

### 5.3 Stage 3 — RDC + 门店联合选址（P-median）

**目的**：在通过 Stage 2 的门店网络（新店 + 既有店）基础上，从合规 RDC 候选点中选出 P 个，最小化全网总成本。

**RDC 全周期成本**：

```
RDC 全周期成本 = CapEx（初始投资）
              + PV（5年运营费用：租金+物业+运营+人工+水电）
              − PV（期末残值）
```

**门店配送成本**：

```
单次配送成本 = 固定成本 + 变动成本 × 距离(km)
年配送频次   = 104 次（每周 2 次）
折现配送成本 = Σ 各年（年配送费 × 销售成长因子 / (1+折现率)^t）
```

**优化目标**（P-median）：

```
给定 P 个开放 RDC，每个门店分配给最近（最低配送成本）的 RDC：

minimize Σ RDC全周期成本(开放的P个RDC)
       + Σ 门店折现配送成本(门店 → 分配的RDC)

约束：同城约束（北京门店只能分配北京 RDC，杭州同理）
```

**场景输出**：对 P=1, 2, 3（可配置）分别输出方案，并标注推荐最优 P 值。

---

## 六、城市参数配置

| 参数 | 北京 | 杭州 | 含义 |
|------|------|------|------|
| `wacc` | 12% | 11% | 加权平均资本成本（折现率） |
| `gross_margin` | 21% | 22% | 毛利率 |
| `variable_cost_rate` | 4.5% | 4.2% | 变动成本率 |
| `tax_rate` | 2.5% | 2.5% | 有效税率 |
| `store_residual_rate` | 15% | 15% | 门店期末残值率 |
| `growth[]` | `[0.9,1.0,1.08,1.12,1.12]` | 同左 | 各年销售成长系数 |
| `delivery_freq` | 104 次/年 | 104 次/年 | 配送频次 |
| `delivery_fixed_cost` | 120 元 | 110 元 | 单次固定配送费 |
| `delivery_var_cost_km` | 3.5 元/km | 3.2 元/km | 单次变动配送费 |
| `npv_threshold_10k` | 25 万 | 28 万 | NPV 通过门槛 |
| `dpp_threshold_years` | 2.5 年 | 2.5 年 | DPP 通过门槛 |
| `rent_cap_per_sqm_day` | 1.8 元/㎡/天 | 1.5 元/㎡/天 | RDC 租金上限 |

**GIS 政策圈**：

| 城市 | 禁区圈名称 | 近似半径 | 业务含义 |
|------|-----------|----------|----------|
| 北京 | 五环内近似圈 | 15.5 km | 蓝牌货车白天禁行区域 |
| 杭州 | 绕城内近似圈 | 12.0 km | 蓝牌货车白天禁行区域 |

---

## 七、RDC 硬约束筛选条件

RDC 候选点须同时满足以下 **8 项硬约束**，任意一项不满足即淘汰：

| 编号 | 约束名称 | 具体要求 |
|------|----------|----------|
| 1 | 蓝牌通行（BLUE_ACCESS） | 支持蓝牌货车进入 |
| 2 | 市区通勤时间（TRAVEL_TIME） | 距城市核心区 ≤ 30 分钟 |
| 3 | 净高（CLEAR_HEIGHT） | 层高 ≥ 6 米 |
| 4 | 装卸月台（LOADING_DOCK） | 具备专用装卸月台 |
| 5 | 三温仓（THREE_TEMP） | 支持常温 / 冷藏 / 冷冻三温存储 |
| 6 | 消防（FIRE_SAFETY） | 消防审查通过 |
| 7 | 扰民风险（DISTURBANCE） | 周边无居民区/学校/医院扰民风险 |
| 8 | 租金上限（RENT_CAP） | 租金 ≤ 城市上限（北京 1.8 元/㎡/天，杭州 1.5 元/㎡/天） |
| 9 | 租约年限（LEASE_TERM） | 剩余租约 ≥ 5 年 |
| 10 | 禁区合规（INNER_RING） | 不在蓝牌通行禁区内 |

---

## 八、系统 API 接口列表

### 8.1 选址优化接口

| 端点 | 方法 | 类型 | 说明 |
|------|------|------|------|
| `/` | GET | HTML | 返回主界面页面 |
| `/api/cities` | GET | JSON | 城市 GIS 元数据（地图中心、禁区半径、默认参数等） |
| `/api/run` | POST | multipart | 上传 CSV 文件运行完整三阶段优化 |
| `/api/run-sample` | POST | form | 使用 `sample_data/` 内置数据运行优化 |
| `/api/validate-rdc-point` | POST | JSON | 校验自定义 RDC 坐标是否在禁区内 |
| `/api/sample/<filename>` | GET | 文件 | 下载内置样例 CSV（stores/rdcs/distances） |

**`/api/run` 请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `store_file` | File (CSV) | 是 | 门店候选点数据 |
| `rdc_file` | File (CSV) | 是 | RDC 候选点数据 |
| `distance_file` | File (CSV) | 否 | 预计算距离矩阵 |
| `focus_city` | string | 否 | `beijing` / `hangzhou` / 空（全部） |
| `max_new_stores` | int | 否 | Stage 2 最多选几家新店（默认 8） |
| `p_values` | string | 否 | Stage 3 P 值，逗号分隔（默认 `1,2,3`） |
| `npv_threshold_10k` | float | 否 | 覆盖默认 NPV 阈值 |
| `dpp_threshold_years` | float | 否 | 覆盖默认 DPP 阈值 |
| `use_road_distance` | bool | 否 | 是否启用高德真实路网距离 |
| `amap_key` | string | 否 | 高德地图 API Key |
| `custom_rdcs_json` | JSON | 否 | 地图上自定义添加的 RDC 点位 |

### 8.2 AI 对话接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `POST /api/chat/stream` | SSE 流式 | **主用**。返回 `text/event-stream`，逐字推送 |
| `POST /api/chat` | 同步 JSON | 降级备用，等待完整回复后一次性返回 |

**SSE 事件格式**：

```json
{"type": "session",  "session_key": "abc123"}          // 拿到会话 key
{"type": "delta",    "text": "当前累积全文..."}          // 每次文字更新
{"type": "done",     "text": "最终完整回复", "session_key": "abc123"}
{"type": "error",    "message": "错误信息"}
```

---

## 九、输入数据格式规范

### 9.1 stores.csv — 门店候选点

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `store_id` | string | 是 | 门店唯一 ID |
| `name` | string | 是 | 门店名称 |
| `city` | string | 是 | `beijing` / `hangzhou` |
| `lat` | float | 是 | 纬度（WGS84） |
| `lon` | float | 是 | 经度（WGS84） |
| `rf_sales_10k` | float | 是 | 参考年销售额（万元） |
| `area_sqm` | float | 是 | 门店面积（㎡） |
| `initial_investment_10k` | float | 是 | 初始投资（万元） |
| `annual_fixed_cost_10k` | float | 是 | 年固定成本（万元） |
| `is_existing` | int (0/1) | 是 | 1=既有门店，0=新候选点 |

> **注**：`is_existing=1` 的既有门店跳过 Stage 1/2 筛选，直接进入 Stage 3 网络配送规划。

### 9.2 rdcs.csv — RDC 候选点

| 字段 | 类型 | 说明 |
|------|------|------|
| `rdc_id` | string | RDC 唯一 ID |
| `name` | string | RDC 名称 |
| `city` | string | `beijing` / `hangzhou` |
| `lat` / `lon` | float | 坐标（WGS84） |
| `area_sqm` | float | 仓库面积（㎡） |
| `initial_investment_10k` | float | 初始投资（万元） |
| `annual_rent_10k` | float | 年租金（万元） |
| `annual_property_10k` | float | 年物业费（万元） |
| `annual_operating_10k` | float | 年运营费（万元） |
| `annual_labor_10k` | float | 年人工费（万元） |
| `annual_utility_10k` | float | 年水电费（万元） |
| `residual_rate` | float | 期末残值率（如 0.25） |
| `rent_per_sqm_day` | float | 实际租金（元/㎡/天） |
| `lease_years` | float | 剩余租约年限 |
| `blue_access` | int (0/1) | 蓝牌货车通行 |
| `core_travel_min` | float | 距核心区通勤时间（分钟） |
| `clear_height_m` | float | 净高（米） |
| `loading_dock` | int (0/1) | 装卸月台 |
| `can_three_temp` | int (0/1) | 三温仓支持 |
| `fire_pass` | int (0/1) | 消防通过 |
| `disturbance_risk` | int (0/1) | 扰民风险（1=有风险，需为 0） |

### 9.3 distances.csv — 距离矩阵（可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| `rdc_id` | string | RDC ID |
| `store_id` | string | 门店 ID |
| `distance_km` | float | 距离（公里） |

> 未提供的 (rdc_id, store_id) 对，系统自动使用 Haversine 球面直线距离补全。

---

## 十、前端模块功能说明

前端为单页应用（SPA），主要分为以下功能区域：

### 10.1 参数控制面板

- **城市切换**：北京 / 杭州 / 全部，切换后自动加载城市默认参数
- **阈值覆盖**：NPV 阈值、DPP 阈值（可手动覆盖默认值）
- **P 值步进器**：控制 Stage 3 的 RDC 数量场景（默认 1,2,3）
- **最大新店数**：Stage 2 搜索的上限
- **路网距离**：可填入高德 API Key 启用真实驾车距离

### 10.2 GIS 地图模块（Leaflet.js）

| 地图视图 | 显示内容 |
|----------|----------|
| Stage 1 地图 | 绿色（通过）/ 红色（未通过）标记 + Popup 现金流迷你折线图 |
| Stage 2 地图 | 蓝色标记（选中新店）+ 300m 橙圈（竞争警示）+ 500m 黄圈（软影响区） |
| Stage 3 地图 | RDC 图标（开放/未开放）+ 门店-RDC 连线（颜色区分城市） |
| 通行禁区圈 | 北京五环 / 杭州绕城 红色虚线圈（政策硬约束提示） |
| 物流带标注 | 北京/杭州各 3 条主要物流带位置（可供 RDC 选址参考） |

**交互功能**：
- 点击地图空白处 → 添加自定义 RDC 候选点（即时校验禁区）
- 三阶段时间轴切换 → 动态切换地图图层
- 地图自动适配边界（autoFit）
- 标记缩放、连线透明度可调节

### 10.3 数据看板

- **汇总卡片**：总候选点数、Stage 1 通过率、Stage 2 选中门店数、最优 P 值等
- **成本分解柱状图**：RDC 成本 vs 配送成本的城市对比
- **情景对比卡片**：P=1 / P=2 / P=3 方案的总成本、最优方案高亮

### 10.4 AI 对话侧边栏

- 聊天历史列表（localStorage 持久化）
- 新建 / 切换 / 重命名对话
- 逐字流式渲染（SSE + fetch ReadableStream）
- session_key 自动保存，跨请求复用对话上下文

---

## 十一、AI 对话模块架构

### 11.1 技术路径演进

| 阶段 | 方案 | 问题 |
|------|------|------|
| 初始版 | 走公网 `wss://yyb-openclaw.site` + 整段阻塞返回 | 公网绕路延迟高；复杂任务等待数分钟无反馈 |
| Plan A | 切换到本机回环 `ws://127.0.0.1:18789` | 节省 200-500ms，但用户感知无本质改善 |
| **Plan D（当前）** | SSE 全链路流式输出 | 首字节从 ~5s 压到 ~500ms；复杂任务实时显示进度 |

### 11.2 关键实现细节

- **WebSocket 连接**：每次请求新建连接，5 步握手协议（challenge → connect → create/subscribe → send → wait）
- **跨线程通信**：WebSocket 在独立 daemon 线程中运行，通过 `queue.Queue` 向主线程传递事件
- **累积全文模式**：服务端推送的是累积全文（非增量 diff），前端直接替换 `textContent`，避免 off-by-one 错误
- **Session 复用**：前端保存 `session_key`，下次请求携带，OpenClaw 可接续上下文
- **超时设置**：SSE 端点 600 秒（应对复杂分析任务），阻塞端点 90 秒

### 11.3 性能日志指标

Flask 日志中可查看以下关键指标：

```bash
# 查看最近 SSE 流式端点的性能日志
grep "openclaw_stream_timing" ~/happymonkey-site/flask.log | tail -20

# 字段说明：
# total=       总耗时（毫秒）
# first_delta= 首字节延迟（核心体验指标）
# reuse_session= 是否复用了已有 session
# reply_len=   最终回复长度（字符数）
```

---

## 十二、部署架构说明

### 12.1 服务器信息

| 项 | 值 |
|----|----|
| 云平台 | 腾讯云 CVM |
| 公网 IP | `43.133.46.51` |
| 访问地址 | http://43.133.46.51:5001 |
| 操作系统 | Ubuntu |
| Python 版本 | 3.12 |
| 监听端口 | `0.0.0.0:5001` |
| 运行方式 | `nohup python3 app.py`（后台常驻） |
| 日志文件 | `~/happymonkey-site/flask.log` |

### 12.2 目录结构

```
~/happymonkey-site/          ← 工作目录（生产代码）
├── app.py                   ← Flask 主程序（API + 路由）
├── optimizer.py             ← 核心优化引擎（三阶段模型）
├── openclaw_client.py       ← OpenClaw WebSocket 客户端
├── main.py                  ← 启动入口
├── requirements.txt         ← Python 依赖
├── start.sh                 ← 启动脚本（注入环境变量）
├── static/
│   ├── app.js               ← 前端逻辑（地图 + 对话 + 看板）
│   └── style.css            ← 样式
├── templates/
│   └── index.html           ← 主页面模板
└── sample_data/
    ├── stores.csv           ← 内置样例门店数据
    ├── rdcs.csv             ← 内置样例 RDC 数据
    └── distances.csv        ← 内置样例距离矩阵
```

### 12.3 敏感配置（环境变量）

所有密钥和运行时配置通过 `start.sh` 注入，**不提交到 Git**：

| 变量名 | 用途 |
|--------|------|
| `DEEPSEEK_TOKEN` | DeepSeek AI API 密钥 |
| `OPENCLAW_TOKEN` | OpenClaw 平台鉴权 Token |
| `OPENCLAW_WS_URL` | OpenClaw WebSocket 地址（当前：`ws://127.0.0.1:18789`） |
| `OPENCLAW_AGENT_ID` | 使用的 Agent ID（当前：`main`） |
| `FLASK_PORT` | 监听端口（默认 5001） |
| `FLASK_DEBUG` | 调试模式（生产应为 0） |

### 12.4 一键部署流程

```bash
# 在本地项目目录执行
cd ~/Desktop/美团商赛/happy_monkey

# 修改代码后一键部署（脚本自动完成 commit→push→服务器pull→重启）
./deploy.sh "本次修改说明"
```

`deploy.sh` 执行链：
```
git add -A  →  git commit  →  git push (SSH)
    →  SSH 到服务器  →  git pull  →  ./start.sh（重启 Flask）
    →  打印日志 + 访问地址
```

---

*文档最后更新：2026-04-16*
