# 关键要点（持续更新）

> 本项目全程遵守的约定、决策与注意事项。改动/踩坑时回填。

## 1. 设计规范（前端）
- 深色科技感：底 `#070b12`、面板玻璃 `rgba(13,20,30,.72)` + `backdrop-filter: blur(12px)`、青蓝强调 `#22d3c6`、1px 青色描边。
- **不要 AI 味**：禁用紫色渐变、禁止 emoji、不滥用光晕/渐变圆斑。状态一律用 CSS 色块/圆点 + 文字。
- 数据读数一律等宽字体（`'SF Mono', Consolas, monospace`）；只系统字体 + 等宽，无 CDN。
- **单页不滚动**：`100dvh` 网格，面板 `min-height:0; overflow:hidden`，只有面板内部允许自滚；不用固定 px 高度，`minmax(0,1fr)` 适应 16:9 / 16:10 与 Windows DPI 缩放。
- 断点：≥1280px 12 列；800–1279px 2 列；<800px 单列内部滚动。
- **「开始采集」= 实时采集启停（不是拍照/注册）**：IdentityPanel 按钮控制 worker 进程生命周期。`POST /api/camera/start` 用 `subprocess.Popen([sys.executable, "manage.py", "camera_worker"], cwd=BASE_DIR, start_new_session=True)` 拉起独立进程（模型加载+开摄像头→MJPEG/SSE 全上线），PID 写 `media/state/worker.pid`，日志 `media/state/camera_worker.log`；`POST /api/camera/stop` 用 `os.killpg(pid, SIGTERM)`（start_new_session 保证它是进程组组长）。`GET /api/camera/status` 合并 PID 存活 + 心跳年龄（<20s 才算 camera_ok），`loading`=进程活着但心跳未新鲜（模型加载中）。按钮三态由「SSE worker_running + 本地 starting/forceStopped」驱动；**SSE 心跳有过期延迟 ~20s，停止后必须用本地标记立即翻转按钮**，不能直接等 SSE。
- **VideoStream 预览状态机**：`live = worker_running && camera_ok` 才挂 `<img src=/api/video/stream>`；`worker_running && !camera_ok` 显示「采集中…」；否则「CAMERA OFF」。`watch(live)` 就绪时重置 `offline` 重连 MJPEG——`<img> @error` 一旦置 offline 不会自愈，必须靠状态变化重置。
- **macOS 摄像头权限（浏览器/worker 双轨）**：worker 的 OpenCV 摄像头与浏览器 `getUserMedia` 是两套独立权限。worker 打不开（`no_camera`）→ 给运行它的终端/conda 在 系统设置→隐私与安全性→摄像头 授权；浏览器 `getUserMedia` 失败 → 给浏览器应用授权（NotAllowedError 常不弹窗）。两者不通用。

## 2. 计算设备策略
- `pick_device()`：`cuda` > `mps` > `cpu`，环境变量 `NEWCELL_DEVICE` 可覆盖。
- **insightface 不支持 MPS**：`ctx_id=0` 仅当 CUDA，否则 `-1`；Mac 上强制 `providers=["CPUExecutionProvider"]`（规避 onnxruntime CoreML provider 的 embedding 不一致）。
- whisper 自动用 CUDA/MPS；transformers pipeline 用 `device=` 参数；MTCNN **MPS 上强制 CPU**（其多尺度金字塔 `adaptive_avg_pool2d` 在 MPS 对非整除尺寸未实现 pytorch#96056，实测必崩）。
- Windows 无 NVIDIA 时自动回退 CPU（所有推理都应能在 CPU 跑，只是慢）。

## 3. 线程与并发（本地模型）
- 结论：**进程内懒加载 + 单例模型 + 加锁**，不跨请求共享模型实例并发推理。
- 采集重构后无独立 worker 进程：`inference.py::start_warmup()` 后台线程串行加载全部模型，置 `_models_ready`；`infer_frame`/`infer_audio` 就绪后直接在请求线程推理（CPU 上 <1s）。
- 模型调用加 `threading.RLock`（`model_loader` 每模型一把）；MPS 下并发 op 可能死锁。**注意必须用 RLock**：请求路径先 `with model_lock` 再调 `get_insightface()`，其内部会二次取锁——非可重入 `Lock` 会自锁死（实测 face_register 挂起几分钟）。RLock 同线程可重入、跨线程仍互斥，安全。
- 懒加载：`runserver` 启动不加载模型，首个 `/api/infer/status` 触发后台 warmup（~1min，期间前端显示加载中）；人脸注册首次（懒）。
- SQLite WAL + busy_timeout；写用短事务 `transaction.atomic()`（warmup 只读缓存、写仅 inference 落库，同一进程内单写入者）。

## 4. 模型映射（已下载于 `models/cache`）
| 模型 | 用途 | 标签/输出 | 备注 |
|---|---|---|---|
| dima806/facial_emotions_image_detection | 表情 7 分类 | angry/disgust/fear/happy/neutral/sad/surprise | id2label: 0 sad,1 disgust,2 angry,3 neutral,4 fear,5 surprise,6 happy |
| superb/wav2vec2-base-superb-er | 语音情绪 4 类 | neu/hap/ang/sad | 英文预训练，情绪跨语言可用 |
| lxyuan/distilbert-base-multilingual-cased-sentiments-student | 文本情感 3 类 | positive/negative/neutral | |
| snakers4/silero-vad | 语音活动检测 | bool | ~1.5MB |
| InsightFace buffalo_sc | 人脸 512 维 embedding | normed_embedding | 阈值 0.35（归一化余弦） |
| openai/whisper tiny | 中文 ASR | text | download_root=models/cache |
- `HF_HOME` / `TRANSFORMERS_CACHE` / `TORCH_HOME` 指向 `models/cache`，避免重下 ~940MB。

## 5. 跨平台（Mac 开发 / Windows 11 + CUDA 部署）
- 摄像头索引：Windows 用 `cv2.CAP_DSHOW`，回退 `[0,1,2,-1]`；Mac 默认 AVFoundation 索引 0。
- Windows DPI 125/150%：前端不用固定 px，全部 `minmax(0,1fr)` + `dvh`。
- MJPEG `<img>` 与 SSE `EventSource` 在 Chrome/Edge/Firefox/Safari 均兼容；开发走 Vite 代理同源，生产 Django 同源。

## 6. 实时与数据流（2026-08-07 重构后）
- **采集 = 浏览器 `getUserMedia`，推理 = HTTP 请求/响应**（旧 worker/SSE/MJPEG 已全部删除）。`useCaptureSession`（`createSharedComposable`）一次取视频+音频：视频给本地 `<video>` 预览（零延迟），节流 `FRAME_MS=3000` canvas→JPEG POST `/api/infer/frame`、`AUDIO_MS=5000` PCM→WAV POST `/api/infer/audio`；结果同步进各面板 ref。无 SSE、无 worker 进程、无 WebSocket。
- **模型进程内懒加载 + 后台预热**：`inference.py::start_warmup()` 线程加载全部模型，`GET /api/infer/status` 触发并返回 `{state: loading|ready}`；前端轮询就绪后启动帧/音频循环。**首载不阻塞首个请求**（画面即时，模型后台加载）。
- **whisper 转录**：5s 一段音频，Silero VAD 判定有语音才跑 whisper tiny（`language="zh"`），CPU 稳态 0.5–0.8s；`TranscriptRecord` 落库。
- **帧推理写库**：每次 infer_frame 写 `ExpressionRecord` + `IdentityRecord`（幂等，history 页面基于 DB 读取）。
- 色彩空间纪律：infer_frame 的 JPEG 解码为 **BGR** numpy 后，MTCNN 要 RGB、表情 pipeline 要 RGB PIL、insightface 要 BGR，逐调用点转换。
- **兼容层**：`/api/expression/latest`、`/api/expression/history`、`/api/identity/current`、`/api/faces` CRUD 保留，前端 History/FaceRegister 仍可用。

## 7. Arduino 生理信号数据（2026-08-08 已落地采集）
- **两块板**（烧录代码在 `scripts/arduino/`）：端口 A = 温湿度+脉搏板（CSV `温度,脉搏,湿度`），端口 B = 皮电板（单值 GSR）；均 115200 波特、20Hz 采样。
- **后端读取**：`engine/physio.py` 进程内后台线程（每端口一线程，懒启动）；每行解析 → 写 `PhysioSample`（原始，保留 1h 周期清理）→ 5s 窗口聚合写 `PhysioRecord`（含 `gsr_avg`）。端口断开自动重试。
- **配置/接口**：`SerialConfig` 单例（enabled/port_a/port_b/baudrate，`/api/settings/serial` GET/PUT）；`/api/serial/ports` 列出可用串口；`/api/physio/latest`（最近样本+聚合+状态）、`/api/physio/history`。
- **前端**：设置页「生理数据采集」节（开关 + 端口 A/B + 波特率，端口可用下拉 datalist）；PhysioChart 实时展示（体温/湿度/皮电大数字 + 脉搏波形 canvas + 端口连接状态点）。
- **本地测试**：`scripts/physio_sim.py` 用 pty 建虚拟串口持续输出两板格式（填进设置即可测全链路）；`scripts/serial_measure.py` 读真实串口测 lines/s、bytes/s、间隔抖动（给板子端的人用）。
- **待后续**：心率 BPM 峰值检测（当前存脉搏波形，非 BPM）；按人基线归一化波形；皮电 → SCL/SCR 紧张度指标；SQLite 上规模后迁 PostgreSQL。

## 7b. macOS 摄像头权限（TCC）
- macOS 上摄像头受隐私保护：**需在 系统设置 → 隐私与安全性 → 摄像头 中给终端（运行 worker 的应用）授权**。
- 报错 `camera access has been denied`：要么授权，要么在终端跑 `tccutil reset Camera` 重置授权状态后再弹窗授权。
- 注意：不同启动方式（`conda run` 包装、直接 python）可能被 TCC 视为不同应用，权限不通用；授权后重新启动 worker。
- **浏览器采集（人脸注册）走 `navigator.mediaDevices.getUserMedia`**：权限由浏览器弹窗 + 系统 TCC 双重管理，与 worker 的 OpenCV 采集相互独立；`localhost` 属安全上下文可直接用，生产需 HTTPS。
- 无头验证摄像头流：Chrome 加 `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` 提供假摄像头（640x480 测试画面），可驱动"打开→拍照→提交"全流程（无真人脸 → 预期 no_face_detected）。

## 8. 已知约束
- SQLite 单写入者：worker 写入、runserver 读取；写用短事务 `transaction.atomic()`。
- 色彩空间纪律：一个 BGR frame；MTCNN 要 RGB numpy、表情 pipeline 要 RGB PIL、insightface 要 BGR numpy，逐调用点转换。
- Vite 代理对 SSE/MJPEG 默认流式不缓冲；若预览卡顿，`<img>` 直连 Django 源（图片无需 CORS）。
- 生产集成：Django 通过 `newcell/views.py::index_view` + 兜底正则（`^(?!admin/|api/|media/|static/).*$`）服务 `static/dist/index.html`，vue-router history 刷新/直链也返回入口。
- 无头浏览器验证：`chrome --headless=new --remote-debugging-port` + python `websocket-client`（连接时 `suppress_origin=True`，否则 Chrome 151 拒绝 Origin）；`--dump-dom` 会在懒加载路由渲染前 dump，需 CDP 等待。
- **CDP 取页面：`/json/list` 必须选 `type=="page"` 的那条，不能取 `[0]`**——列表可能混有 newtab/扩展页，取错会连到一个空白页，误判为"前端没挂载"（本次排查假警报的根因）。诊断时先 `Runtime/Log/Network/Page.enable` 再 `Page.navigate`，统一收集 console/network 失败/异常，避免黑盒猜。
- **CDP 消息 id 必须为整数**：`{"id": <method名>}` 会被 Chrome 以 `Message must have integer 'id' property` 拒绝且**不回 id 匹配的响应**，`recv()` 循环将一直等 → 表现为 `Connection timed out`（排查了半小时的"连接超时"实为 id 类型错误）。
- **Python `urllib`/`http.client` 无法访问 Chrome DevTools HTTP 服务**（`RemoteDisconnected: Remote end closed connection without response`），`curl http://127.0.0.1:9222/json/list` 正常——脚本里取 targets 一律用 `curl` 子进程。
- **无头 E2E 假摄像头**：`--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` 提供 640x480 测试画面；`useCaptureSession` 验证流程「面板渲染→点开始采集→`video.srcObject` 有 videoTrack→按钮翻转→MODEL ready→停止复位→无 console error」。假画面无真人脸 → 表情/身份预期 NO FACE（属正确行为）。
- **MPS 在当前 conda env 不可用**：`torch.backends.mps.is_available()==False`（torch 2.13.0），全部推理走 CPU；warmup 完成后真实人脸帧推理 <1s。
- `RegisteredFace.person_name` 唯一 → 重注册 upsert 覆盖 embedding。
- 人脸注册首次调用会懒加载 insightface（~1min），之后即时。
