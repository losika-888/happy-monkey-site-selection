# Happy Monkey 网站云端部署说明

## 一、部署概览

| 项 | 值 |
| --- | --- |
| 公网访问地址 | http://43.133.46.51:5001 |
| 服务器 | 腾讯云 CVM,IP `43.133.46.51`(内网 `10.3.0.17`) |
| 登录用户 | `ubuntu` |
| SSH 密钥 | `/Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem` |
| 服务器项目目录 | `~/happymonkey-site/` |
| 服务器裸仓库(Git 远端) | `~/happymonkey-site.git` |
| Python 版本 | 3.12(系统自带) |
| 虚拟环境 | `~/happymonkey-site/venv` |
| 监听端口 | `0.0.0.0:5001`(腾讯云安全组已放行) |
| 日志文件 | `~/happymonkey-site/flask.log` |
| 启动脚本 | `~/happymonkey-site/start.sh` |

---

## 二、架构与数据流

```
本地开发机 (Mac)                      腾讯云 VPS (43.133.46.51)
─────────────────                     ────────────────────────────
~/Desktop/.../happy_monkey            ~/happymonkey-site.git   (裸仓库 / Git 远端)
   │                                         │
   │  git push (SSH + key)                   │  git pull
   └────────────────────────────────►        ▼
                                      ~/happymonkey-site        (工作目录)
                                         │
                                         ├── venv/              (Python 虚拟环境)
                                         ├── start.sh           (启动 / 重启脚本 + 环境变量)
                                         ├── flask.log          (运行日志)
                                         └── app.py ...         (项目代码)
                                                │
                                                ▼  0.0.0.0:5001 (nohup 后台)
                                                │
                                  浏览器 ◄──── SSE 流式 ────┐
                                                │           │
                                                ▼           │
                                      OpenClaw (ws://127.0.0.1:18789)
                                        同机本地回环,无 TLS / 无公网往返
```

- **代码同步走 Git**:服务器上跑着一个裸仓库 `~/happymonkey-site.git`,作为本地 git 的 `origin`。本地 `git push` 推到裸仓库,服务器再从裸仓库 `git pull` 到工作目录 `~/happymonkey-site`。
- **OpenClaw 走本机 WebSocket**:Flask 通过 `openclaw_client.py` 连 `ws://127.0.0.1:18789`(OpenClaw 本地监听端口),**同机直连**,不再绕公网 `wss://yyb-openclaw.site` + Nginx 反代。详见下文「OpenClaw 接入方式演进」。
- **前端 ↔ Flask 用 SSE 流式输出**:`/api/chat/stream` 端点把 OpenClaw 的 `agent.stream=assistant` 事件实时转发给浏览器,文字逐字显示,复杂任务体感大幅提升。旧的 `/api/chat`(一次性返回)作为降级备份保留。
- **敏感信息走环境变量**:`DEEPSEEK_TOKEN`、`OPENCLAW_TOKEN` 等已从代码中移除,由 `start.sh` 在启动时注入。

---

## 三、首次部署做了什么(备忘)

1. 代码改造
   - `app.py` 的 `host/port/debug` 改为读 `FLASK_HOST` / `FLASK_PORT` / `FLASK_DEBUG` 环境变量
   - `DEEPSEEK_TOKEN` 硬编码改为 `os.environ.get("DEEPSEEK_TOKEN", "")`
   - `openclaw_client.py` 的 `WS_URL` / `TOKEN` / `AGENT_ID` 改为读环境变量
   - `requirements.txt` 补充 `websocket-client`
   - 添加 `.gitignore`(忽略 `venv/`、`__pycache__/`、`*.log`)

2. 服务器端
   - `git init --bare ~/happymonkey-site.git`(裸仓库作为 origin)
   - `git clone ~/happymonkey-site.git ~/happymonkey-site`
   - `python3 -m venv venv && pip install -r requirements.txt`
   - 创建 `start.sh` 注入环境变量并 `nohup` 启动
   - 腾讯云安全组放行 TCP 5001

3. 本地端
   - `git init` → `git remote add origin ubuntu@43.133.46.51:happymonkey-site.git`
   - `git push -u origin main`

---

## 四、日常改代码的流程

### 推荐方式:用一键脚本

本地项目根目录下已经有 `deploy.sh`,用法:

```bash
cd ~/Desktop/美团商赛/happy_monkey

# 1. 正常在本地修改任何文件(app.py / templates/*.html / static/* 等)
# 2. 改完直接运行:
./deploy.sh "修复了 xxx 问题"
```

脚本会自动完成:

1. `git add -A && git commit -m "你的提交信息"`
2. `git push` 到服务器裸仓库(用正确的 SSH key)
3. SSH 到服务器执行 `git pull`
4. 调用 `start.sh` 杀掉旧的 Flask 进程、重新 `nohup` 启动
5. 打印最近几行日志 + 访问地址

如果没传提交信息,默认用 `update`。如果本地没改动,会跳过 commit 只重启服务器。

### 手动方式(脚本出问题时的后备)

```bash
# 本地
cd ~/Desktop/美团商赛/happy_monkey
git add -A
git commit -m "xxx"
GIT_SSH_COMMAND="ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem" git push origin main

# SSH 到服务器
ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem ubuntu@43.133.46.51

# 在服务器上
cd ~/happymonkey-site
git pull origin main
./start.sh
tail -f flask.log      # 按 Ctrl+C 退出查看
```

### 改了依赖(`requirements.txt`)怎么办

`start.sh` 只会重启进程,不会重装依赖。如果你加了新的 pip 包,需要手动装一次:

```bash
ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem ubuntu@43.133.46.51
cd ~/happymonkey-site
source venv/bin/activate
pip install -r requirements.txt
./start.sh
```

---

## 五、常用运维命令

全部在 SSH 进服务器后执行:

```bash
ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem ubuntu@43.133.46.51
```

| 目的 | 命令 |
| --- | --- |
| 查看实时日志 | `tail -f ~/happymonkey-site/flask.log` |
| 查看最近 50 行日志 | `tail -50 ~/happymonkey-site/flask.log` |
| 确认 Flask 是否在跑 | `pgrep -af "python3 app.py"` |
| 确认端口在监听 | `ss -tlnp \| grep 5001` |
| 手动重启 | `~/happymonkey-site/start.sh` |
| 停止服务 | `pkill -f "python3 app.py"` |
| 从外部测试首页 | `curl -I http://43.133.46.51:5001/` |

---

## 六、修改运行时配置(端口 / Token 等)

所有运行时配置都集中在服务器上的 `~/happymonkey-site/start.sh`。这个文件**不在 git 里**(只存在于服务器),改它需要 SSH 进去编辑:

```bash
ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem ubuntu@43.133.46.51
nano ~/happymonkey-site/start.sh
# 改完保存,然后:
~/happymonkey-site/start.sh
```

里面可以调的变量:

- `FLASK_PORT` —— 监听端口(改了记得去腾讯云安全组同步放行)
- `FLASK_DEBUG` —— 设为 `1` 开启调试模式(生产别开)
- `DEEPSEEK_TOKEN` —— DeepSeek API key
- `OPENCLAW_TOKEN` / `OPENCLAW_WS_URL` / `OPENCLAW_AGENT_ID` —— OpenClaw 接入参数

---

## 七、常见问题排查

**问:`deploy.sh` 报 `Permission denied (publickey)`**
→ 确认本地密钥路径 `/Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem` 存在,且权限是 `400`/`600`(`chmod 600 <key>`)。

**问:浏览器打不开 http://43.133.46.51:5001,但服务器本地 `curl 127.0.0.1:5001` 是 200**
→ 99% 是腾讯云安全组没放行端口。去控制台 → 安全组 → 入站规则,确认 `TCP:5001` 对 `0.0.0.0/0` 放行。

**问:`./start.sh` 后 `flask.log` 里报 `ModuleNotFoundError`**
→ 新加了依赖但没装。进 venv `pip install -r requirements.txt` 后再重启。

**问:AI 聊天窗口无响应 / 报 OpenClaw 错误**
→ 按顺序排查:
1. `ss -tln | grep 18789` —— OpenClaw 本机端口是不是还在监听
2. `tail -50 ~/happymonkey-site/flask.log` —— 看 Flask 有无报错堆栈
3. `cat /proc/$(pgrep -f "python3 app.py")/environ | tr "\0" "\n" | grep OPENCLAW` —— 确认 Flask 进程加载的 `OPENCLAW_WS_URL` 是 `ws://127.0.0.1:18789` 而不是旧的 `wss://...`
4. `grep openclaw_stream_timing ~/happymonkey-site/flask.log | tail` —— 看最近几次调用的耗时和首字延迟

**问:浏览器里聊天窗口不再逐字显示,又变成整段出来了**
→ 多半是浏览器缓存了旧的 `static/app.js`。硬刷新一次(Mac: Cmd+Shift+R)。
→ 如果还不行,DevTools → Network 面板看 `/api/chat/stream` 这个请求有没有发出,Content-Type 是不是 `text/event-stream`。

**问:服务器重启后 Flask 没自动起来**
→ 当前用 `nohup` 没配 systemd 自启。重启后 SSH 进去跑一次 `./start.sh` 即可。如果以后需要开机自启,可以再加 systemd service。

---

## 八、OpenClaw 接入方式演进(性能优化记录)

本节记录本项目接入 OpenClaw 的架构从"公网远程调用 + 整段阻塞返回"演进到"本机直连 + SSE 流式输出"的过程,以及为什么要这样改。

### 背景问题

最初版本的问题:
1. **走公网绕路**:Flask 和 OpenClaw 明明在同一台腾讯云 VPS 上,但 Flask 通过 `wss://yyb-openclaw.site` 连 OpenClaw —— 每次请求都走 公网 DNS → TLS 握手 → Nginx 反代 → 再绕回本机,白白多一大段延迟。
2. **整段阻塞返回**:`/api/chat` 用 `openclaw_chat()` 同步等 OpenClaw 把完整回复跑完才整段返回给浏览器。复杂任务动辄几分钟,用户对着"思考中..."干瞪眼,体感非常差。

### Plan A:OpenClaw 走本机回环

**改动**:`start.sh` 里 `OPENCLAW_WS_URL` 从 `wss://yyb-openclaw.site` 改为 `ws://127.0.0.1:18789`(OpenClaw 本地监听端口)。

**原理**:OpenClaw 和 Flask 同机部署,Nginx 本来就是先 TLS 解密再转发到 `127.0.0.1:18789`。Flask 直接跳过 Nginx,省掉 TLS 握手 + 公网往返,所有协议握手 RTT 从几十毫秒级压到毫秒级。

**代码改动**:零。`openclaw_client.py` 的 `WS_URL` 本来就是读环境变量的,只改 `start.sh`。

**效果**:协议层握手开销约省 200~500ms,但远远解决不了"复杂任务要几分钟"的核心痛点。

### Plan D:前后端全链路 SSE 流式输出

**核心洞察**:OpenClaw 本来就是以 `agent.stream=assistant` 事件形式**流式推送**累积文本的,只是旧代码把这些事件屯起来等结束才一起返回。真正让用户觉得"快"的方式是让字**一个一个冒出来**,而不是缩短总耗时。

**改动范围**:

| 文件 | 改动 |
| --- | --- |
| `openclaw_client.py` | 新增 `openclaw_chat_stream()` generator,基于 `queue.Queue` 做跨线程桥梁,yield `{type:'session'\|'delta'\|'done'\|'error'}` 事件。旧的 `openclaw_chat()` 保留不动。 |
| `app.py` | 新增 `POST /api/chat/stream` 端点,把 generator 转成 `text/event-stream`(SSE)。响应头带 `X-Accel-Buffering: no` 防止反代缓冲。旧的 `/api/chat` 保留作为降级备份。 |
| `static/app.js` | `chatSend()` 改用 `fetch + res.body.getReader()` 手工解析 SSE 帧,收到 `delta` 就 `textContent = ev.text`(推累积全文,不算增量,避免 off-by-one bug);收到 `session` 立刻保存 `session_key`;收到 `done` 收尾。 |

**关键决策**:
- **累积全文 vs 增量 delta**:选累积全文。因为 OpenClaw 协议本来就推累积,算 delta 只会引入 bug。
- **EventSource vs fetch+ReadableStream**:选后者。EventSource 只支持 GET,前端需要 POST 带 messages 数组。
- **超时值**:从 90s → 600s。复杂任务经常几分钟。
- **旧端点是否删除**:**不删**。`/api/chat` 长期保留作为降级备份,只有 30 行,成本极低。

**效果**:
- 短对话:首字节从 ~5s 压到 ~500ms,总时间不变但感知提升巨大。
- 复杂任务:之前等 3 分钟才看到字,现在几秒就开始持续写字,从"不可用"变"流畅"。
- `session_key` 在拿到的当下就推给前端,即使后面网络断了也能复用会话。

### 相关端点与日志

- `POST /api/chat/stream` —— **主用**,SSE 流式。前端通过 `fetch + ReadableStream` 读取。
- `POST /api/chat` —— 旧端点,同步整段返回,降级备份。
- 计时日志:
  - `[openclaw_chat_timing]` —— 旧端点耗时(`elapsed` / `reuse_session` / `reply_len`)
  - `[openclaw_stream_timing]` —— 新端点耗时(`total` / `first_delta` / `reuse_session` / `reply_len`)。**`first_delta` 是关键指标**,代表用户从发消息到看到第一个字的时间。

查看最近的计时数据:
```bash
ssh -i /Users/philyang/Desktop/Oepn_Claw/Open_Claw.pem ubuntu@43.133.46.51 \
  'grep -E "openclaw_(chat|stream)_timing" ~/happymonkey-site/flask.log | tail -20'
```

---

## 九、后续可做的改进(非必需)

- [ ] **Plan B:OpenClaw 长连接池 + session 缓存**。在 Flask 进程内维护常驻 WebSocket,复用 `connect` 握手和已订阅的 session,可再省 20~150ms 的首字节时间。对体感提升有限,按需再做。
- [ ] 用 Gunicorn + Nginx 反代替代 Flask 开发服务器(生产级)。注意 SSE 长连接需要在 Nginx 上关掉 `proxy_buffering`,并加大 `proxy_read_timeout`。
- [ ] 配置 systemd 实现服务器重启后 Flask 自动拉起
- [ ] 给服务器裸仓库加 `post-receive` hook,实现 `git push` 后自动部署(省掉 deploy.sh 里那一步 ssh)
- [ ] 绑定域名 + Let's Encrypt HTTPS
