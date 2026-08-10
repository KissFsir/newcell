import { ref, watch } from 'vue'
import { createSharedComposable } from '@vueuse/core'
import { api } from '../api/client'
import { useTranscriptionMode, isWebSpeechSupported } from './useTranscriptionMode'

const FRAME_MS = 3000 // 帧推理间隔
const AUDIO_MS = 5000 // 音频切段上传间隔
const AUDIO_SECONDS = 5 // 每段音频时长
const STATUS_POLL_MS = 2000

/**
 * 共享浏览器采集会话：getUserMedia 视频+音频 → 本地预览流；
 * 节流上行帧到 /api/infer/frame（表情/身份始终本地模型）；
 * 转录按 useTranscriptionMode 二选一：
 *   local —— 音频节流上行 /api/infer/audio（后端 whisper）
 *   api   —— 浏览器 Web Speech API 直接识别（谷歌，不走后端）
 * 替代原 SSE（useSnapshotStream）与 worker 启停。
 */
function useCaptureSessionRaw() {
  const { mode } = useTranscriptionMode()
  const running = ref(false)
  const modelState = ref('idle') // idle | loading | ready | error
  const error = ref('')
  const stream = ref(null)
  const videoEl = ref(null)
  const analyser = ref(null)

  const expression = ref({ available: false })
  const identity = ref({ available: false })
  const transcriptItems = ref([])
  const voice = ref({ speaking: false, level: 0 })
  const interimText = ref('') // Web Speech API 实时中间结果
  const speechSupported = isWebSpeechSupported()

  let audioCtx = null
  let recorder = null
  let analyserNode = null
  let pcmBuf = []
  let pcmTotal = 0
  let frameTimer = null
  let audioTimer = null
  let statusTimer = null
  let recognition = null // Web Speech Recognition 实例

  function setVideoEl(el) {
    videoEl.value = el
    if (el && stream.value) el.srcObject = stream.value
  }

  function _mapError(e) {
    if (e?.name === 'NotAllowedError') return '摄像头/麦克风权限被拒绝，请在浏览器地址栏允许访问'
    if (e?.name === 'NotFoundError') return '未检测到摄像头或麦克风设备'
    if (e?.name === 'NotReadableError') return '摄像头被其他应用占用'
    return e?.message || '采集启动失败'
  }

  function _setupAudio(mediaStream) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    audioCtx = new AudioCtx()
    const src = audioCtx.createMediaStreamSource(mediaStream)

    analyserNode = audioCtx.createAnalyser()
    analyserNode.fftSize = 2048
    analyserNode.smoothingTimeConstant = 0.7
    src.connect(analyserNode)
    analyser.value = analyserNode

    recorder = audioCtx.createScriptProcessor(4096, 1, 1)
    pcmBuf = []
    pcmTotal = 0
    const maxSamples = audioCtx.sampleRate * (AUDIO_SECONDS + 1)
    recorder.onaudioprocess = (e) => {
      const ch = e.inputBuffer.getChannelData(0)
      const copy = new Float32Array(ch.length)
      copy.set(ch)
      pcmBuf.push(copy)
      pcmTotal += ch.length
      while (pcmTotal > maxSamples && pcmBuf.length) {
        pcmTotal -= pcmBuf.shift().length
      }
      let sum = 0
      for (let i = 0; i < ch.length; i++) sum += ch[i] * ch[i]
      voice.value.level = Math.min(1, Math.sqrt(sum / ch.length) * 4)
    }
    const gain = audioCtx.createGain()
    gain.gain.value = 0
    src.connect(recorder)
    recorder.connect(gain)
    gain.connect(audioCtx.destination)
    if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {})
  }

  function _buildWav() {
    if (!audioCtx) return null
    const sr = audioCtx.sampleRate
    const take = Math.floor(sr * AUDIO_SECONDS)
    let flat = []
    let len = 0
    for (let i = pcmBuf.length - 1; i >= 0 && len < take; i--) {
      flat.unshift(pcmBuf[i])
      len += pcmBuf[i].length
    }
    if (len === 0) return null
    const total = Math.min(len, take)
    const samples = new Float32Array(total)
    let off = total
    for (const buf of flat) {
      if (off <= 0) break
      const n = Math.min(off, buf.length)
      samples.set(buf.subarray(buf.length - n), off - n)
      off -= n
    }
    return _encodeWav(samples, sr)
  }

  function _encodeWav(samples, sampleRate) {
    const buf = new ArrayBuffer(44 + samples.length * 2)
    const dv = new DataView(buf)
    const ws = (off, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(off + i, s.charCodeAt(i)) }
    ws(0, 'RIFF'); dv.setUint32(4, 36 + samples.length * 2, true); ws(8, 'WAVE')
    ws(12, 'fmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true)
    dv.setUint32(24, sampleRate, true); dv.setUint32(28, sampleRate * 2, true)
    dv.setUint16(32, 2, true); dv.setUint16(34, 16, true)
    ws(36, 'data'); dv.setUint32(40, samples.length * 2, true)
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      dv.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return new Blob([buf], { type: 'audio/wav' })
  }

  async function _captureFrame() {
    const video = videoEl.value
    if (!video || !video.videoWidth) return null
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.8))
  }

  function _pollStatus() {
    api.get('/api/infer/status')
      .then((s) => {
        modelState.value = s.state === 'ready' ? 'ready' : 'loading'
        if (s.state === 'ready') {
          _startLoops()
          return
        }
        if (running.value) statusTimer = setTimeout(_pollStatus, STATUS_POLL_MS)
      })
      .catch(() => {
        if (running.value) statusTimer = setTimeout(_pollStatus, 3000)
      })
  }

  function _startLoops() {
    _frameLoop()
    if (mode.value === 'local') _audioLoop()
  }

  async function _frameLoop() {
    if (!running.value) return
    const blob = await _captureFrame()
    if (blob) {
      const fd = new FormData()
      fd.append('file', blob, 'frame.jpg')
      try {
        const r = await api.upload('/api/infer/frame', fd)
        expression.value = {
          available: !!r.available,
          dominant_emotion: r.dominant_emotion,
          confidence: r.confidence,
          face_image: r.face_image,
        }
        identity.value = {
          available: !!r.identity,
          person_name: r.identity?.person_name || 'unknown',
          confidence: r.identity?.confidence ?? 0,
          is_unknown: r.identity?.is_unknown ?? true,
          gender: r.identity?.gender || '',
          student_no: r.identity?.student_no || '',
          major: r.identity?.major || '',
        }
      } catch (e) {
        // 瞬时失败跳过本轮
      }
    }
    if (running.value) frameTimer = setTimeout(_frameLoop, FRAME_MS)
  }

  async function _audioLoop() {
    // 仅本地模型模式上传；切到 api 后下次调用直接返回（定时器链自然中断）
    if (!running.value || mode.value !== 'local') return
    const blob = _buildWav()
    if (blob) {
      const fd = new FormData()
      fd.append('file', blob, 'audio.wav')
      try {
        const r = await api.upload('/api/infer/audio', fd)
        voice.value.speaking = !!r.has_speech
        if (r.has_speech && r.transcript) {
          const d = new Date()
          const label = d.toLocaleTimeString('zh-CN', { hour12: false })
          transcriptItems.value.unshift({ text: r.transcript, timeLabel: label })
          if (transcriptItems.value.length > 30) transcriptItems.value.length = 30
        }
      } catch (e) {
        // 瞬时失败跳过本轮
      }
    }
    if (running.value) audioTimer = setTimeout(_audioLoop, AUDIO_MS)
  }

  let recognitionError = false

  function _startSpeechRecognition() {
    if (!speechSupported || recognition) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    recognition = new SR()
    recognitionError = false
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'zh-CN'
    recognition.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) {
          const text = r[0].transcript.trim()
          if (text) {
            const d = new Date()
            transcriptItems.value.unshift({
              text,
              timeLabel: d.toLocaleTimeString('zh-CN', { hour12: false }),
              source: 'api',
            })
            if (transcriptItems.value.length > 30) transcriptItems.value.length = 30
          }
        } else {
          interim += r[0].transcript
        }
      }
      interimText.value = interim
      voice.value.speaking = !!interim || e.results[e.results.length - 1].isFinal
    }
    recognition.onend = () => {
      // Chrome 静音/超时会自动停止，运行中、仍为 api 且无持久错误才重启
      if (running.value && mode.value === 'api' && !recognitionError) {
        try { recognition?.start() } catch (e) { /* 已启动则忽略 */ }
      }
    }
    recognition.onerror = (ev) => {
      if (ev.error === 'no-speech' || ev.error === 'aborted') return // 正常静音，等待重启
      recognitionError = true // 权限/网络等持久错误：停止自动重启，避免死循环
      if (ev.error === 'not-allowed') {
        error.value = '麦克风权限被拒绝，无法使用 Web Speech 识别'
      }
    }
    try {
      recognition.start()
    } catch (e) {
      // 偶发"已启动"抛错，忽略
    }
  }

  function _stopSpeechRecognition() {
    if (recognition) {
      recognition.onend = null
      recognition.onresult = null
      recognition.onerror = null
      try { recognition.abort() } catch (e) {}
      recognition = null
    }
    recognitionError = false
    interimText.value = ''
  }

  async function start() {
    if (running.value) return
    try {
      const ms = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      stream.value = ms
      running.value = true
      error.value = ''
      modelState.value = 'idle'
      voice.value.speaking = false
      _setupAudio(ms)
      if (videoEl.value) videoEl.value.srcObject = ms
      if (mode.value === 'api') _startSpeechRecognition()
      _pollStatus()
    } catch (e) {
      error.value = _mapError(e)
    }
  }

  function stop() {
    running.value = false
    clearTimeout(frameTimer)
    clearTimeout(audioTimer)
    clearTimeout(statusTimer)
    _stopSpeechRecognition()
    voice.value.speaking = false
    if (recorder) { recorder.onaudioprocess = null; recorder.disconnect() }
    if (audioCtx) audioCtx.close().catch(() => {})
    audioCtx = null
    recorder = null
    analyserNode = null
    analyser.value = null
    pcmBuf = []
    pcmTotal = 0
    stream.value?.getTracks().forEach((t) => t.stop())
    stream.value = null
    if (videoEl.value) videoEl.value.srcObject = null
    modelState.value = 'idle'
  }

  function toggle() {
    if (running.value) stop()
    else start()
  }

  // stream 变化时兜底刷新预览（组件晚挂载场景）
  watch(stream, (s) => {
    if (videoEl.value) videoEl.value.srcObject = s
  })

  // 转录方式运行中切换：实时切换转录源
  watch(mode, (m) => {
    if (!running.value) return
    if (m === 'api') {
      clearTimeout(audioTimer)
      _stopSpeechRecognition()
      _startSpeechRecognition()
    } else {
      _stopSpeechRecognition()
      if (modelState.value === 'ready') _audioLoop()
    }
  })

  return {
    running, modelState, error, stream, videoEl, analyser,
    expression, identity, transcriptItems, voice, interimText,
    mode, speechSupported,
    start, stop, toggle, setVideoEl,
  }
}

export const useCaptureSession = createSharedComposable(useCaptureSessionRaw)
