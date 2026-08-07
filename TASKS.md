# 任务清单（实时更新，`[x]` 表示完成）

> 环境：conda `newcell` ｜ 前端：Vue3+Vite ｜ 实时：SSE 3s ｜ 设备：cuda>mps>cpu

## Phase 0 — 仓库卫生 + 基础设施
- [x] 创建 `.gitignore`（media/、db.sqlite3、models/cache、face_db.pkl、node_modules、dist、static/dist、__pycache__、.idea）
- [x] `git rm -r --cached models/cache .idea`（清除已暂存的 ~940MB 模型与 IDE 文件）
- [x] 创建 `requirements.txt` 并安装（注意：安装时曾把 torch 降级到 2.2.2，已用 `pip install torch==2.13.0 torchvision==0.28.0 torchaudio==2.11.0` 还原；requirements 已钉版本防再降级）
- [x] 创建 `TASKS.md`（本文件）与 `KEYPOINTS.md`
- [x] 安装 skills：`frontend-ui-engineering`、`vueuse-core-skilld`

## Phase 1 — Django 骨架 + 数据模型
- [x] 创建 `newcell/apps/` 包 + 5 个 app（accounts 桩 / physio / speech 仅模型 / expression / records 完整），注册 `INSTALLED_APPS`
- [x] 定义全部模型：`PhysioRecord`、`ExpressionRecord`、`IdentityRecord`、`RegisteredFace`、`SpeechEmotionRecord`、`TranscriptRecord`、`EmotionSnapshot`
- [x] `settings.py`：模型缓存 env、SQLite WAL/busy_timeout、MEDIA/STATIC、时区、常量
- [x] 所有模型注册 admin
- [x] `makemigrations` + `migrate` 成功（WAL 已生效）

## Phase 2 — engine 推理进程
- [x] `engine/device.py`：`pick_device()`（cuda>mps>cpu + NEWCELL_DEVICE 覆盖）、`pick_insightface_ctx()`
- [x] `engine/model_loader.py`：懒加载单例 + 每模型 `threading.Lock`，MTCNN **MPS 强制 CPU**（adaptive_avg_pool2d 在 MPS 对非整除尺寸未实现，实测必崩）
- [x] `engine/stream_store.py`：原子写 `latest.jpg` + `heartbeat.json`
- [x] `engine/camera_worker.py` + 管理命令：5s 推理循环（MTCNN→表情→insightface→匹配→写库）
- [x] 跑通：`test_infer.py` 空帧推理生成 `ExpressionRecord`+`IdentityRecord`（dominant=none 符合预期）；预览帧/心跳由 stream_store 验证

## Phase 3 — API（含 SSE + MJPEG）
- [x] `/api/stream`：SSE 每 3s 推最新快照（expression+identity+status）
- [x] `/api/expression/latest` + `/api/expression/history`
- [x] `/api/identity/current`
- [x] `/api/faces` CRUD（list / register(blank→400 no_face_detected) / delete(404)）
- [x] `/api/video/stream`：MJPEG 预览（--frame 分块 + JFIF 验证）
- [x] `/api/snapshot` 兜底 + `/api/records/history`
- [x] `newcell/urls.py` 挂载 `api/` + media 服务（DEBUG）
- [x] **修复**：`model_lock` 从 `Lock` 改为 `RLock`（face_register 先持锁再调 get_insightface() 内部二次取锁 → 非可重入 Lock 自锁死，实测挂起）

## Phase 4 — Vue 3 + Vite 前端
- [x] 脚手架 `frontend/`（vue3+vite+router+@vueuse/core+echarts）+ vite proxy
- [x] 设计令牌 + 全局样式 + 100dvh 网格（不滚动、断点 1280/800）
- [x] `useSnapshotStream`（SSE useEventSource 封装）—— **修复**：`useEventSource` 第二参 events 传 `null` 会抛 `events is not iterable`，改传 `undefined`
- [x] App 壳 + StatusBar + 路由
- [x] ExpressionPanel（CSS 横条）+ EmotionBadge
- [x] VideoStream（MJPEG `<img>`）+ IdentityPanel
- [x] FaceRegister（上传/列表/删除）
- [x] History / Login 桩页 + Dashboard 网格布线
- [x] **headless Chrome/CDP 验证**：Dashboard 四面板 + EmotionBadge + 7 情绪横条 + SSE 数据（LINK ok/WORKER warn/UPDATE）全部渲染、`/faces` 表单+列表渲染、无滚动（app-shell 高度=视口、scrollY=0）

## Phase 5 — 集成 + 端到端验证
- [x] `npm run build` → `static/dist`，`newcell/views.py::index_view` + SPA 兜底路由（非 api/media/static/admin）从 :8000 服务 Dashboard
- [x] 端到端验证：无滚动（app-shell 高度=视口）、SSE 3s 推送、MJPEG 分块、表情/身份面板、人脸注册（400 no_face）、worker 运行→LINK ok/WORKER ok、停 worker ~26s 后 worker_running=false（状态灯转黄）
- [x] **追加需求（人脸录入）**：注册页支持**浏览器摄像头拍照采集**（getUserMedia → canvas → JPEG dataURL → multipart 上传），保留文件上传备选；fake-camera 无头验证全流程（开摄像头 640x480 → 拍照 → 提交 → no_face）；后端错误码前端中文化（no_face_detected→未检测到人脸等）
- [x] **主页面「开始采集」= 实时采集启停**（用户澄清：要的是主页面实时摄像头预览，不是弹窗拍照，也不是注册）：点「开始采集」→ `POST /api/camera/start` 用 subprocess 拉起 `manage.py camera_worker`（`start_new_session` + PID 落盘 `media/state/worker.pid` + 日志 `media/state/camera_worker.log`），worker 开摄像头 → MJPEG 预览 + 表情/身份识别（SSE）全部上线；再点「停止采集」→ `POST /api/camera/stop` `os.killpg(SIGTERM)`。按钮三态：开始采集 / 采集中…（模型加载，轮询 `GET /api/camera/status` 的 `loading`）/ 停止采集；停止后本地 `forceStopped` 立即翻转（SSE 心跳有 ~20s 过期延迟，不能直接依赖）。删除 `FaceCaptureModal.vue`（死代码）。
- [x] **VideoStream 自动恢复**：预览面板按 `worker_running`/`camera_ok` 显示 实时图 / 采集中… / CAMERA OFF；`watch(live)` 在 worker 就绪时自动重连 MJPEG（此前 `<img> @error` 一次失败永久 offline，worker 起来后不会恢复）。
- [x] **无头验证（真实摄像头，非 fake）**：`camera/start` → `camera/status`（camera_ok=true、心跳 0.1s）→ worker 日志出 `infer ok: identity=曾逸韩 (0.67)`（真实注册人脸被识别）→ `latest.jpg` 刷新 142KB → `camera/stop` → status running=false。UI 闭环：开始采集→采集中…→停止采集→点停止立即回开始采集。
- [x] 勾选全部清单 + 回填 `KEYPOINTS.md`
- [x] **headless Chrome CDP 验证**：`websocket-client`（suppress_origin=True 规避 Chrome 151 Origin 拒绝）+ `--remote-debugging-port`；`useEventSource` 传 `undefined` 而非 `null`（`events is not iterable` 已修复）

## 当前问题与需求（2026-08-07 用户反馈，已记录未实现）
- [ ] **问题① 启动延迟**：点「开始采集」后要**等很久**才调用摄像头/出画面——worker 先加载模型再开摄像头（首载 ~1min）。方向：开摄像头与模型加载并行（先出画面再加载）；或前端展示加载阶段/进度。
- [ ] **问题② SSE 导致显示不流畅**：SSE 推送疑似让前端画面/数据更新不流畅。待排查：3s 整段突跳 vs MJPEG 同页资源竞争 vs EventSource 重连中断。
- [ ] **需求③ 采集源改为浏览器摄像头**：数据采集应由**浏览器 `getUserMedia`** 完成（而非 worker 的 OpenCV）。方向：浏览器连续取帧 → 上传后端推理 → 返回表情/身份结果；worker 角色需重新设计（可能改为纯推理服务），涉及前端帧上传通道 + 后端推理接口 + 结果回传。
- [ ] **需求④ 表情只显示当前主情绪**：前端不再展示 7 类概率（去掉概率横条），只显示当下的情绪是什么。
- [ ] **需求⑤ 左侧布局改版**：左侧新增「声纹」框 + 「语音实时转录（中文）」框；实时转录接 ASR（whisper），声纹语义（说话人识别/声纹特征？）待确认。

## 未来工作（保持未勾选）
- [ ] 麦克风 worker：VAD + SER + ASR + 文本情感（speech app 落地）
- [ ] Arduino 生理信号（双串口）：端口 A=心率+温湿度、端口 B=皮电；`PhysioRecord` 落库
- [ ] 生理前端：体温直接大数字展示；心率波形图（按各人基线相对化，波形一致但数值因人而异）；湿度折线图
- [ ] 生理数据**每次新增都落库**（曲线基于 DB 历史，刷新/回放不丢数据）
- [ ] 皮电 → GSR：SCL 低通基线 + SCR 峰值检测，输出紧张/唤醒指标（先基础版，后续改进）
- [ ] ECharts 历史时间线 + CSV 导出 + 每日摘要
- [ ] 登录/注册 + 令牌认证 + CSRF 硬化（accounts app 落地）
- [ ] Windows CUDA 真机验证（摄像头索引、DPI 125/150%）
