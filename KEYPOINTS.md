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
- 结论：**进程隔离 + 单线程推理 + 加锁**，不跨线程共享模型。
- `camera_worker` 独立进程、串行循环推理 → 无并发。
- Django 请求路径（人脸注册）的模型调用加 `threading.RLock`；MPS 下并发 op 可能死锁。**注意必须用 RLock**：请求路径先 `with model_lock` 再调 `get_insightface()`，其内部会二次取锁——非可重入 `Lock` 会自锁死（实测 face_register 挂起几分钟）。RLock 同线程可重入、跨线程仍互斥，安全。
- 懒加载：`runserver` 启动不加载模型，只在 worker 启动（~1min）与人脸注册首次（懒）。
- 多进程唯一共享 SQLite → WAL + busy_timeout + 单写入者；后续 mic/arduino 沿用"每进程单写入者"，规模大了再考虑 PostgreSQL。

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

## 6. 实时与数据流
- **待办方向（2026-08-07 用户确认）**：数据采集计划从 worker 的 OpenCV 摄像头**改为浏览器 `getUserMedia`**——前端连续取帧上传后端推理、回传表情/身份结果；当前 worker 开摄像头 + 写 latest.jpg + MJPEG 的架构届时会被重构成「纯推理服务」。涉及前端帧上传通道、后端推理接口、结果回传；同时去掉前端 7 类概率展示（只显示当前主情绪），左侧新增声纹 + 中文实时语音转录框。本节的 worker/SSE/MJPEG 描述在改造落地前仍为当前事实。
- worker 推理 5s（准实时约束），SSE 每 3s 重读最新记录推送 → 新推理落库后展示延迟 ≤3s。两者节奏不同是有意取舍。
- 前端 `useEventSource('/api/stream')` 第二参 events **必须传 `undefined` 而非 `null`**（`null` 不可迭代 → 抛 `events is not iterable`，组件 setup 全挂）。默认已含 message，勿传数组。
- 状态来源：`media/state/heartbeat.json` 心跳，超过 ~20s 无更新视为 worker 停止（前端状态灯转黄）。
- 摄像头预览：MJPEG 由 worker 原子写 `media/frames/latest.jpg`（跨进程文件共享，非内存），Django 读 mtime 分块输出。
- MJPEG/SSE 响应必须带 `Cache-Control: no-store/no-cache`，否则浏览器缓存首块后冻结。

## 7. Arduino 生理信号数据（未来阶段，需求已确认）
- **两个串口/端口传回**：端口 A = 心率 + 体表温度 + 皮肤湿度；端口 B = 皮电（皮肤电导，原始值）。
- **体温**：前端直接大数字展示（当前值 + 单位 °C），不用图表。
- **心率**：用**波形/折线图**，重点做适配——波形波动形态一致，但**不同人的基线/量级不同**，展示时应按各自基线归一化/相对化（如显示相对波动或自动缩放 Y 轴），不能写死刻度。
- **湿度**：折线图（趋势，非实时大数字）。
- **皮电 → GSR（皮肤电反应）**：原始皮电信号做分析可得：
  - SCL（皮电水平 / tonic，缓慢基线）—— 低通滤波获得；
  - SCR（皮电反应 / phasic，事件性尖峰）—— 高频成分 + 峰值检测；
  - 可据此给"紧张度/唤醒度"指标（EDA 领域常用）。
  - 先做基础版（滤波 + 均值/峰值统计），后续改进（事件相关 SCR、峰谷检测）。
- 端口策略：Python 端两个串口各自一个读取进程/线程，数据按时间戳落库；前端同一曲线区展示。
- **每次新增的数据点都要落库**（不仅是实时推给前端）：前端曲线基于 DB 历史读取，刷新页面/回放时仍能拿到完整数据，不会因只流式展示而丢失。

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
- **CDP 取页面：`/json/list` 必须选 `type=="page"` 的那条，不能取 `[0]`**——列表可能混有 newtab/扩展页，取错会连到一个空白页，误判为"前端没挂载"（本次排查假警报的根因）。诊断时先 `Runtime/Log/Network/Page.enable` 再 `Page.navigate`，统一收集 console/network 失败/异常，避免黑盒猜。无头装 `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` 提供假摄像头驱动"打开→拍照→提交"。
- `RegisteredFace.person_name` 唯一 → 重注册 upsert 覆盖 embedding。
- 人脸注册首次调用会懒加载 insightface（~1min），之后即时。
