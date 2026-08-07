# PRD: 浏览器采集重构 + 实时语音面板（Dashboard 改版）

## Introduction

当前系统由后端 `camera_worker` 进程用 OpenCV 打开摄像头采集，通过 MJPEG 推预览、SSE 每 3s 推快照。用户反馈三个问题：**启动延迟**（worker 先加载模型再开摄像头，首载约 1 分钟才出画面）、**SSE 显示不流畅**（3s 整段突跳）。同时确认三个新需求：**采集源改为浏览器 `getUserMedia`**、**表情只显示当前主情绪**（去掉 7 类概率条）、**左侧新增「声纹」框 +「中文实时转录」框**。本 PRD 将采集源整体移到浏览器，后端收敛为「纯推理服务」，简化表情展示，并新增音频活动指示与实时中文转录。

## Goals

- 点「开始采集」后摄像头预览**立即**出现（<1s），不再等模型加载完才出画面。
- 后端不再通过 OpenCV 直接采集；采集、推理在架构上解耦为「浏览器采集 → 后端推理」。
- 表情面板只显示当前主情绪 + 置信度，移除 7 类概率横条。
- 左侧新增「声纹」框（有声音/有人讲话时波形波动）+「中文实时转录」框（whisper ASR）。
- 数据更新平滑：推理完成后结果即刻到达界面，消除 3s SSE 突跳。

## User Stories

- 作为用户，我想在点击「开始采集」后立刻看到自己的摄像头画面，而不是等约 1 分钟，以便快速确认采集是否就绪。
- 作为用户，我想一眼看到当前情绪是什么（而不是七根概率条），以便快速读懂面板。
- 作为用户，我想在左侧看到「有人说话、声纹在波动」的实时指示，以及我说的话实时转成中文文字，以便核对语音采集是否生效。
- 作为用户，我希望画面与数据显示平滑连贯，不出现整段卡顿/突跳。

## Functional Requirements

1. **浏览器采集（视频）**：点「开始采集」后通过浏览器 `getUserMedia` 打开摄像头，预览**立即**出现（测试点：预览出现在点击后 1s 内，不依赖后端模型加载）。
2. **帧上传与推理**：浏览器持续将视频帧上传后端推理接口；后端返回该帧的表情主情绪 + 置信度 + 身份（姓名/未知）。帧上传需节流（建议 ≤2fps，640×480）以控制带宽与算力。
3. **表情只显示主情绪**：表情面板仅展示当前主情绪（中文标签）+ 置信度；7 类概率横条移除（测试点：面板中不再出现概率横条）。
4. **浏览器采集（音频）**：音频同样走浏览器 `getUserMedia`（麦克风），连续采集并切分片段上传。
5. **VAD + ASR**：后端对音频片段跑 VAD；判定无人声时返回 silent，前端转录框不更新；判定有人声时跑中文 ASR（whisper），返回转录文本。
6. **「声纹」框**：表示「附近有声音 / 有人讲话」的实时活动指示——有声音时波形/指示波动，安静时回落；由本地 Web Audio（AnalyserNode）即时驱动 + 后端 VAD 状态佐证（测试点：说话时波动、静音时稳定）。
7. **「中文实时转录」框**：展示最近一段语音的中文转录文字，随推理结果滚动更新（测试点：说话后转录文字在 ~3s 内出现并持续追加）。
8. **「开始采集」语义变更**：按钮改为启停**浏览器采集**（getUserMedia 视频 + 音频），不再拉起后端 worker 进程。模型加载与采集解耦：画面先出，模型加载期间界面显示「模型加载中」，加载完成后推理结果开始到达。
9. **流畅度**：摄像头展示用浏览器本地视频流（`<video>` + `srcObject`，无网络延迟）；推理结果经 **HTTP 请求-响应**即时回传并更新界面（前端节流上行帧/音频；测试点：单次推理完成后界面 ~1s 内可见更新，无 3s 整段突跳）。
10. **结果落库**：表情/身份/转录结果仍按现有模型写库（ExpressionRecord / IdentityRecord / TranscriptRecord），供历史回放使用（测试点：DB 中持续产生新记录）。

## Non-Functional Requirements

- 实时性：推理节奏保持 ~5s（准实时）；转录从讲话到展示延迟目标 ≤3s。
- 单用户、中文场景；单人脸取面积最大者，与现状一致。
- 跨浏览器：Chrome/Edge/Firefox/Safari 的 `getUserMedia` 均可（localhost 为安全上下文；生产需 HTTPS）。
- 跨平台：Mac 开发 / Windows 11 + CUDA 部署不受影响；浏览器采集天然规避了 OpenCV 摄像头索引/驱动差异。
- 沿用现有单页不滚动布局（100dvh 网格、断点 1280/800），新面板融入现有网格。
- 模型推理沿用现有 `pick_device()`（cuda > mps > cpu）与锁纪律（进程隔离 + 单线程 + RLock）。
- 色彩空间纪律：一条 BGR 帧链路上 MTCNN(RGB)/pipeline(RGB PIL)/insightface(BGR) 逐调用点转换，保持现状约定。

## Non-Goals

- **SER（语音情绪）与文本情感展示**不在本次范围，转录框只显示文字，不显示情绪标签。
- **「声纹」不做说话人识别/说话人区分**：仅为「有声音/有人讲话」的活动指示。
- **WebSocket 通道不在 v1**：推理结果走 HTTP 请求-响应即时返回（前端节流上行，结果随响应驱动 UI）；WS（更低延迟/常驻推送）作为后续增强。
- **独立推理 worker 进程不在 v1**：模型在 Django 进程内懒加载复用（`engine/model_loader.py`）；`camera_worker` 停用而非重构为独立推理服务。
- Arduino 生理信号、历史回放/CSV 导出、登录认证、Windows CUDA 真机验证：均为后续阶段。
- 不引入多说话人、多人脸融合、概率可视化。
- 不做数据采集的降采样/压缩优化（本次只要求可用的帧/音频上传通道）。

## Design Considerations

- 布局目标：左列新增两个面板「声纹」与「中文实时转录」。当前网格为 12 列（expression 1-5、video 5-9、identity 5-9 row6、physio 9-13）；改版后需重排，典型目标布局：顶部 EmotionBadge 全宽；中列视频 + 身份/采集控制；左列声纹 + 转录；右列保留生理占位。具体网格在 `frontend/src/styles/grid.css` 调整。
- 表情面板缩为「主情绪大字 + 置信度」，可与 EmotionBadge 语义合并（避免重复展示），具体交互在实现时定。
- 视频预览由 `<img src=/api/video/stream>`（MJPEG）改为浏览器本地视频流（`<video>` + `srcObject`），天然低延迟、无需后端转发。
- 「声纹」波形：本地 `AnalyserNode.getByteTimeDomainData` 实时驱动，无需为波动频繁上传音频；后端 VAD 结果只用于标注「有人讲话/安静」状态。
- 音频片段长度沿用 5s（与 5s 推理节奏一致），VAD 静音则丢弃不推理、不上传 ASR。

## Technical Considerations

- **v1 后端（演示优先精简）**：Django 进程内懒加载模型（复用 `engine/model_loader.py` 的懒加载 + RLock + `device.py::pick_device`），暴露两个推理接口：`POST /api/infer/frame`（MTCNN→表情→insightface→身份匹配）与 `POST /api/infer/audio`（silero VAD → 有语音才 whisper zh ASR）。**不做独立 worker 进程、不做 WS**。
- 模型加载：懒加载 + 常驻缓存。首次推理调用可能 ~1min（模型加载），返回/暴露「模型加载中」状态（`GET /api/infer/status`），不阻塞预览出现（预览是浏览器本地流）。加载完成后每次推理秒级返回。
- 帧上传通道：浏览器 canvas → JPEG blob → POST（multipart 或 base64）→ 后端推理 → 响应即时返回。建议 ≤2fps、640×480。
- 音频上传通道：浏览器 AudioContext/MediaRecorder 切 5s 片段 → POST → VAD（现有 silero-vad）→ 有人声再跑 ASR（现有 whisper tiny, language=zh）→ 返回转录文本。
- 传输取舍：v1 用 HTTP 请求-响应（前端节流上行，结果随响应驱动 UI），不再依赖 SSE/MJPEG/WS；`camera_worker` 停用（OpenCV 采集、MJPEG 写帧、心跳、`camera_start/stop` 子进程控制全部移除）。WS 与独立推理服务列入后续增强。
- 复用现有资产：`engine/device.py::pick_device`、`engine/model_loader.py`（模型 + 锁）、`engine/stream_store.py`（心跳，按需保留）、人脸注册/匹配逻辑（`_match_registered`）、`api/client.js` 请求层。
- DB：模型已存在，预计**无需 schema 变更**；沿用 SQLite WAL + 单写入者纪律。
- 被移除/改造清单：`/api/video/stream`、`/api/stream`（SSE）、`/api/camera/start|stop`、`latest.jpg`/MJPEG 链路、OpenCV 摄像头索引逻辑（`_open_camera` 及 DSHOW 分支）。

## Implementation Surface

- **Frontend / UI**：`frontend/src/views/Dashboard.vue`、`frontend/src/styles/grid.css`；新增 `VoiceActivityPanel.vue`（声纹）、`TranscriptPanel.vue`（转录）；改造 `ExpressionPanel.vue`（去概率条）、`VideoStream.vue`（浏览器 `<video>` 预览）、`IdentityPanel.vue`（采集启停→getUserMedia）；`frontend/src/api/client.js`（新增 infer 接口）；`frontend/src/composables/useSnapshotStream.js` 改版为 WS 消费（`useInferSocket`），SSE 移除。
- **Backend / API**：新增 `POST /api/infer/frame`、`POST /api/infer/audio`、`GET /api/infer/status`；移除/改造 `/api/video/stream`、`/api/stream`、`/api/camera/start|stop`；主要改动 `newcell/apps/expression/views.py`（或新增推理视图），复用 `engine/model_loader.py`。
- **Database**：复用 `ExpressionRecord` / `IdentityRecord` / `TranscriptRecord`；预计无迁移。
- **Background jobs**：`camera_worker.py` 改造为纯推理服务（移除采集循环）；`run_worker.py` / 管理命令相应调整。
- **External integrations**：无新增。
- **Infrastructure**：Vite 代理不变；无新增部署依赖。

## Success Metrics

- 「开始采集」→ 预览出现 < 1s（原 ~1min）。
- 表情面板仅剩主情绪 + 置信度，7 类概率条消失。
- 「声纹」框：说话时波动、静音时回落（对照 VAD 状态一致）。
- 转录框：讲话后转录文字 ≤3s 出现并持续追加；静音时不产生新文本。
- 界面无 3s 整段突跳；单次推理完成后 ≤1s 内界面可见更新。
- DB 持续写入 ExpressionRecord / IdentityRecord / TranscriptRecord 新行。

## Open Questions

- 推理服务生命周期：常驻进程 vs 首次请求惰性拉起（由设计期决定，owner: tech-lead）。
- 帧上传频率与分辨率取多少（建议 ≤2fps、640×480，设计期定，owner: tech-lead）。
- 表情结果是否继续每 ~5s 落库一行（倾向保留，供历史回放；owner: tech-lead）。
- 左列新面板在 <1280px / <800px 断点下的排布（owner: 前端）。
- SER / 文本情感：本次明确**不做**，确认后续作为独立 PRD。

## Next Steps

推荐下一步：**`generate-tasks`** —— PRD 批准后将其拆为带验收门槛的实现任务。

备选链路：`plan-tickets`（生成可跟踪的 ticket）。
