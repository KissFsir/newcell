<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'
import { EMOTION_ZH, EMOTION_COLOR } from '../constants/emotions'
import { api } from '../api/client'

const RESULT_MS = 10000 // AI 洞察自动刷新间隔

const { running, modelState, error, expression, identity, transcriptItems, toggle } = useCaptureSession()

const dominant = computed(() => (expression.value?.available ? expression.value.dominant_emotion : null))
const conf = computed(() => expression.value?.confidence ?? null)
const zh = computed(() => (dominant.value ? EMOTION_ZH[dominant.value] || dominant.value : '—'))
const color = computed(() => (dominant.value ? EMOTION_COLOR[dominant.value] : 'var(--text-dim)'))
const btnLabel = computed(() => (running.value ? '停止采集' : '开始采集'))
const loading = computed(() => running.value && modelState.value === 'loading')

const resultItems = ref([]) // { timeLabel, text, model }，新分析结果在前
const resultLoading = ref(false)
const resultError = ref('')
let timer = null

async function fetchResult() {
  if (!running.value || modelState.value !== 'ready' || resultLoading.value) return
  resultLoading.value = true
  resultError.value = ''
  try {
    const r = await api.post('/api/infer/result', {
      emotion: dominant.value || 'none',
      confidence: conf.value ?? 0,
      person_name: identity.value?.available ? identity.value.person_name : 'unknown',
      transcript: transcriptItems.value.slice(0, 3).map((i) => i.text).join(' '),
    })
    if (r.error) {
      resultError.value = r.error
    } else {
      const d = new Date()
      resultItems.value.unshift({
        timeLabel: d.toLocaleTimeString('zh-CN', { hour12: false }),
        text: r.result,
        model: r.model || '',
      })
      if (resultItems.value.length > 50) resultItems.value.length = 50
    }
  } catch (e) {
    resultError.value = e.message || 'AI 分析失败'
  } finally {
    resultLoading.value = false
  }
}

watch([running, modelState], () => {
  clearInterval(timer)
  timer = null
  if (running.value && modelState.value === 'ready') {
    fetchResult()
    timer = setInterval(fetchResult, RESULT_MS)
  }
})

onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="panel panel-result">
    <div class="panel-title">
      <span>情感洞察</span>
      <span class="hint">INSIGHT</span>
    </div>
    <div class="panel-body result-body">
      <button class="btn-capture mono" :class="{ stop: running }" type="button" @click="toggle">
        {{ btnLabel }}
      </button>
      <p v-if="loading" class="result-msg mono">模型加载中，首次约 1 分钟…</p>
      <p v-else-if="error" class="result-msg mono">{{ error }}</p>

      <div class="result-emotion">
        <span class="emotion-label">最终主情绪</span>
        <span class="emotion-value mono" :style="{ color }">{{ zh }}</span>
        <span v-if="dominant" class="emotion-meta mono">
          {{ dominant }} · CONF {{ conf != null ? (conf * 100).toFixed(0) + '%' : '--' }}
        </span>
      </div>

      <div class="result-ai">
        <div class="ai-head">
          <span class="ai-title mono">AI 洞察</span>
          <button class="btn-refresh mono" type="button" :disabled="!running || resultLoading" @click="fetchResult">
            {{ resultLoading ? '分析中…' : '刷新' }}
          </button>
        </div>
        <p v-if="resultLoading" class="ai-msg mono ai-loading">正在分析…</p>
        <p v-if="resultError" class="ai-msg mono ai-error">{{ resultError }}</p>
        <ul v-if="resultItems.length" class="ai-list">
          <li v-for="(item, i) in resultItems" :key="i" class="ai-item">
            <span class="ai-time mono">{{ item.timeLabel }}</span>
            <span class="ai-text">{{ item.text }}</span>
            <span v-if="item.model" class="ai-model mono">{{ item.model }}</span>
          </li>
        </ul>
        <p v-if="!resultItems.length && !resultLoading && !resultError" class="ai-msg mono ai-empty">
          开始采集后自动分析
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.btn-capture {
  align-self: flex-start;
  padding: 10px 22px;
  font-size: 14px;
  letter-spacing: 0.08em;
  background: rgba(34, 211, 198, 0.12);
  border: 1px solid rgba(34, 211, 198, 0.4);
  color: var(--accent);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.btn-capture:hover {
  background: rgba(34, 211, 198, 0.2);
}

.btn-capture.stop {
  background: rgba(242, 95, 92, 0.12);
  border-color: rgba(242, 95, 92, 0.4);
  color: var(--danger);
}

.result-msg {
  margin: 0;
  font-size: 11px;
  color: var(--warn);
}

.result-emotion {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 0;
  border-top: 1px solid var(--panel-border);
  border-bottom: 1px solid var(--panel-border);
}

.emotion-label {
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--text-dim);
}

.emotion-value {
  font-size: 52px;
  font-weight: 700;
  letter-spacing: 0.1em;
  line-height: 1.1;
}

.emotion-meta {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.1em;
}

.result-ai {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-title {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--text-dim);
}

.btn-refresh {
  padding: 4px 10px;
  font-size: 11px;
  background: transparent;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  color: var(--text-dim);
  cursor: pointer;
}

.btn-refresh:hover:not(:disabled) {
  color: var(--accent);
  border-color: rgba(34, 211, 198, 0.4);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-msg {
  margin: 0;
  font-size: 12px;
}

.ai-loading {
  color: var(--accent);
}

.ai-empty {
  color: var(--text-dim);
}

.ai-error {
  color: var(--warn);
}

.ai-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-item {
  display: flex;
  gap: 10px;
  align-items: baseline;
  font-size: 13px;
  line-height: 1.6;
}

.ai-time {
  flex: 0 0 auto;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.05em;
}

.ai-text {
  flex: 1 1 auto;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-model {
  flex: 0 0 auto;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.05em;
}
</style>
