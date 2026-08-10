import { ref, watch } from 'vue'

const STORAGE_KEY = 'newcell.asr.mode' // 'local' | 'api'

/**
 * 转录方式共享单例（模块级 ref）：Settings 页与采集会话共用。
 * 'local' = 浏览器采集音频 → 后端 /api/infer/audio（whisper 本地模型）
 * 'api'   = 浏览器内置 Web Speech API（谷歌识别），不走后端
 * 选择持久化到 localStorage。
 */
const mode = ref(localStorage.getItem(STORAGE_KEY) === 'api' ? 'api' : 'local')

watch(mode, (m) => {
  localStorage.setItem(STORAGE_KEY, m)
})

export function useTranscriptionMode() {
  return { mode }
}

/** 浏览器是否支持 Web Speech API（Chrome/Edge/Safari 支持，Firefox 不支持） */
export function isWebSpeechSupported() {
  return typeof window !== 'undefined' &&
    !!((window.SpeechRecognition) || (window.webkitSpeechRecognition))
}
