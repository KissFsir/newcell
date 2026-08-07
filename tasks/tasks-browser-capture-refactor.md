# Task List: 浏览器采集重构 + 实时语音面板（v1 演示优先精简版）

基于: `prd-browser-capture-refactor.md`（v1 精简范围）

> **范围声明**：本版砍掉 WS 与独立推理 worker（改 HTTP 请求-响应 + Django 进程内懒加载模型），目标 ~1.5–2 周出可正确演示的前端。WS/独立推理服务列为后续增强。

## 工程约定（已检测）

- 后端测试命令（已验证）: `source /opt/anaconda3/etc/profile.d/conda.sh && conda activate newcell && python manage.py test`
- 后端测试目录: `newcell/apps/*/tests.py`
- 前端测试: `frontend/package.json` 无测试脚本 → 用项目既有 **headless Chrome + CDP** 验证（KEYPOINTS §8：fake-camera/fake-audio + `--remote-debugging-port` + websocket-client + `suppress_origin=True`，取 `/json/list` 的 `type=="page"`）
- 模型/推理单测一律 **mock 模型**（真实模型 ~940MB、首载 ~1min，不进入单测）

## Relevant Files

- `newcell/engine/model_loader.py` — 模型懒加载 + RLock（复用，不重写）
- `newcell/engine/device.py` — `pick_device()`（复用）
- `newcell/engine/camera_worker.py` — **停用**（移除 OpenCV 采集/MJPEG/心跳/`camera_start|stop` 引用）
- `newcell/apps/expression/views.py` — 新增 `infer_frame` / `infer_audio` / `infer_status`；移除 SSE/MJPEG/camera 控制
- `newcell/apps/expression/models.py` — ExpressionRecord/IdentityRecord/RegisteredFace（复用，写库）
- `newcell/apps/speech/models.py` — TranscriptRecord（复用，写库）
- `frontend/src/composables/useBrowserCapture.js` — 新建：getUserMedia 视频+音频启停
- `frontend/src/composables/useInferLoop.js` — 新建：节流上行帧/音频，收推理结果
- `frontend/src/components/VideoStream.vue` — `<video>+srcObject` 本地预览
- `frontend/src/components/ExpressionPanel.vue` — 主情绪 + 置信度（去 7 类概率条）
- `frontend/src/components/IdentityPanel.vue` — 采集启停 + 「模型加载中」
- `frontend/src/components/VoiceActivityPanel.vue` — 新建：声纹波形
- `frontend/src/components/TranscriptPanel.vue` — 新建：中文转录
- `frontend/src/views/Dashboard.vue` + `frontend/src/styles/grid.css` — 布局重排 + 断点
- `frontend/src/api/client.js` — infer/status 接口

## Tasks

- [ ] 0.0 安全基线提交：仓库当前**零提交**，先 `git add` 相关文件 + `git commit` 留回退点
- [ ] 0.1 创建 feature 分支：`git checkout -b feature/browser-capture-refactor`

- [ ] 1.0 后端推理接口（Django 进程内懒加载模型）
  - [ ] **1.0s Spike（whisper 转录延迟）**：用 `models/demo_asr.py` 实测 whisper tiny 对 5s 音频的转录延迟与 MPS 兼容性；结论回填到转录节奏（目标 5s 片段转录 ≤3s）。若 MPS 不可用则明确 CPU 方案
  - [ ] 1.1a 写失败测试：`infer_frame(bgr, mock_models)` 无人脸→`{dominant:"none"}`；有人脸→表情+身份（mock model_loader）
  - [ ] 1.1b 运行测试命令 — 确认失败
  - [ ] 1.1c 实现 `POST /api/infer/frame`（MTCNN→表情→insightface→匹配；写 ExpressionRecord/IdentityRecord）
  - [ ] 1.1d 运行测试命令 — 确认通过
  - [ ] 1.2a 写失败测试：`infer_audio(wav, mock)` 无语音→`{has_speech:false}`；有语音→`{has_speech:true, transcript:"…"}`（写 TranscriptRecord）
  - [ ] 1.2b 运行测试命令 — 确认失败
  - [ ] 1.2c 实现 `POST /api/infer/audio`（silero VAD → 有语音才 whisper zh）
  - [ ] 1.2d 运行测试命令 — 确认通过
  - [ ] 1.3 `GET /api/infer/status` 返回模型加载状态（loading/ready/error）；移除 `/api/video/stream`、`/api/stream`、`/api/camera/start|stop`（tests：移除后 404）；停用 `camera_worker` 管理命令/run_worker
  - [ ] 1.4 回归：`/api/faces` CRUD、RLock 纪律不回退（KEYPOINTS §3）；`manage.py test` 全绿

- [ ] 2.0 前端浏览器采集 + 本地预览
  - [ ] 2.1 新建 `useBrowserCapture.js`：getUserMedia（video+audio）启停、权限/无设备错误中文化
  - [ ] 2.2 `VideoStream.vue` 改 `<video>+srcObject` 本地流；去掉 MJPEG `<img>` 与 offline 逻辑
  - [ ] 2.3 `IdentityPanel.vue` 按钮改为启停浏览器采集；模型未就绪显示「模型加载中」（读 `/api/infer/status`）
  - [ ] 2.4 CDP 验证：fake-camera 打开→画面出现→停止→按钮复位

- [ ] 3.0 前端表情/身份展示（来自推理响应）
  - [ ] 3.1 新建 `useInferLoop.js`：连接推理循环（节流上行帧 ≤2fps，接收结果），断线/请求失败重试
  - [ ] 3.2 `ExpressionPanel.vue` 只显示主情绪 + 置信度（复用 EMOTION_ZH/COLOR）；删除 7 条概率 bar
  - [ ] 3.3 身份展示：姓名/置信度/未知；无数据时占位（沿用 identity 面板语义）
  - [ ] 3.4 CDP 验证：fake-camera 下面板随推理响应更新、无 `.bar-row` 概率横条

- [ ] 4.0 前端声纹 + 中文实时转录
  - [ ] 4.1 新建 `VoiceActivityPanel.vue`：`AnalyserNode` 实时波形（本地驱动）+ 说话/安静状态（来自 VAD 结果）
  - [ ] 4.2 音频上传：浏览器 5s 切段 → `POST /api/infer/audio` → 结果驱动转录
  - [ ] 4.3 新建 `TranscriptPanel.vue`：中文转录滚动展示（含时间戳）
  - [ ] 4.4 CDP 验证：fake-audio 输入语音→转录出现并滚动；静音不新增；声纹波形随音频波动

- [ ] 5.0 布局 + 集成 + 端到端
  - [ ] 5.1 `Dashboard.vue` + `grid.css`：左列声纹+转录、中列视频+身份/控制、右列生理占位；断点 1280/800；单页不滚动保持
  - [ ] 5.2 真实摄像头+麦克风端到端：开始采集→画面即时出现→表情/身份/声纹/转录全链路→停止
  - [ ] 5.3 确认 DB 持续写 ExpressionRecord / IdentityRecord / TranscriptRecord（历史回放数据）
  - [ ] 5.4 更新 `TASKS.md`（勾选）、`KEYPOINTS.md`（回填：infer 接口协议/帧节流/模型状态/旧链路废弃）、`models/README.md`（如需）

- [ ] 6.0 文档 + 代码评审
  - [ ] 6.1 文档化 `/api/infer/frame`、`/api/infer/audio`、`/api/infer/status` 请求/响应
  - [ ] 6.2 自审 diff（复用既有工具、无死代码、KEYPOINTS 纪律不回退）

## 工作量估算（时间范围框架，2026-08-07，v1 精简）

| ID | 任务 | 估算 | 置信度 | 备注 |
|----|------|------|--------|------|
| 0.x | 基线提交 + 建分支 | <1d | 高 | 零提交代码入库 |
| 1.0 | 后端推理接口（frame/audio/status + 清理） | 2-3d | 中 | 含 whisper spike；进程内懒加载模型 |
| 2.0 | 前端采集 + 本地预览 | 1-2d | 中高 | getUserMedia 模式可复用 FaceRegister |
| 3.0 | 表情/身份展示（主情绪 + 推理循环） | 1-2d | 中 | useInferLoop 节流/重试逻辑 |
| 4.0 | 声纹 + 转录 | 1-2d | 中 | AnalyserNode 独立；转录依赖 1.0 |
| 5.0 | 布局 + 集成 + E2E | 2-3d | 中低 | 真实设备 E2E 排障不可控 |
| 6.0 | 文档 + 评审 | <1d | 高 | 协议文档 + 自审 |

**合计 ≈ 9–14 人日 ≈ 2–3 周**（单人），相比完整版（~23d）大幅缩短。

**砍掉**：WS（HTTP 请求-响应替代）、独立推理 worker（进程内懒加载）、camera_worker 重构（直接停用）。

**风险项**：① 1.0s whisper spike 是前置门禁，转录延迟不达标则 4.x 节奏调整；② 5.0 E2E 真实设备排障低置信度，预留缓冲；③ 浏览器与后端同机跑模型，开发机内存需 ≥940MB 空闲。

**依赖链**：1.0→3.x/4.x；3.0/4.0→5.0。1.0 是唯一后端块，做完即全链路可通。

## 验证方式

1. 后端单测：每任务四元组跑 `python manage.py test`
2. 前端：每切片 headless Chrome CDP 验证（fake-camera / fake-audio）
3. 端到端：真实设备全链路（Task 5.2）
