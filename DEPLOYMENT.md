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
                                         ├── start.sh           (启动 / 重启脚本)
                                         ├── flask.log          (运行日志)
                                         └── app.py ...         (项目代码)
                                                │
                                                ▼
                                      0.0.0.0:5001 (nohup 后台进程)
                                                │
                                                ▼
                                      OpenClaw (wss://yyb-openclaw.site)
```

- **代码同步走 Git**:服务器上跑着一个裸仓库 `~/happymonkey-site.git`,作为本地 git 的 `origin`。本地 `git push` 推到裸仓库,服务器再从裸仓库 `git pull` 到工作目录 `~/happymonkey-site`。
- **OpenClaw 走远程 WebSocket**:Flask 通过 `openclaw_client.py` 连 `wss://yyb-openclaw.site`,**不依赖** OpenClaw 本地 workspace 文件。
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
→ 检查 `start.sh` 里 `OPENCLAW_TOKEN` 是否正确;`tail -50 flask.log` 看报错堆栈。

**问:服务器重启后 Flask 没自动起来**
→ 当前用 `nohup` 没配 systemd 自启。重启后 SSH 进去跑一次 `./start.sh` 即可。如果以后需要开机自启,可以再加 systemd service。

---

## 八、后续可做的改进(非必需)

- [ ] 用 Gunicorn + Nginx 反代替代 Flask 开发服务器(生产级)
- [ ] 配置 systemd 实现服务器重启后 Flask 自动拉起
- [ ] 给服务器裸仓库加 `post-receive` hook,实现 `git push` 后自动部署(省掉 deploy.sh 里那一步 ssh)
- [ ] 绑定域名 + Let's Encrypt HTTPS
