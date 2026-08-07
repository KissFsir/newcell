<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useSnapshotStream } from '../composables/useSnapshotStream'
import { api } from '../api/client'

const { snapshot } = useSnapshotStream()

const identity = computed(() => snapshot.value?.identity)

const name = computed(() => {
  if (!identity.value?.available) return 'NO FACE'
  return identity.value.person_name
})

const confidence = computed(() => identity.value?.confidence ?? null)

const isUnknown = computed(() => identity.value?.is_unknown ?? false)

const stale = computed(() => {
  if (!identity.value?.available) return true
  return (identity.value.age_seconds ?? 99) > 15
})

// ---- 实时采集启停（worker 进程） ----
const workerRunning = computed(() => !!snapshot.value?.status?.worker_running)

const busy = ref(false)
const starting = ref(false)
const forceStopped = ref(false)
const camMsg = ref('')
let pollTimer = null
let stopPoll = false

// SSE 心跳有过期延迟（~20s），停止后本地立即翻转按钮
watch(workerRunning, (on) => {
  if (on) forceStopped.value = false
})

const captureLabel = computed(() => {
  if (busy.value) return '处理中…'
  if (starting.value) return '采集中…'
  if (forceStopped.value || !workerRunning.value) return '开始采集'
  return '停止采集'
})

const captureBusy = computed(() => busy.value || starting.value)

function pollStatus() {
  stopPoll = false
  const tick = async () => {
    if (stopPoll.value) return
    let s = null
    try {
      s = await api.get('/api/camera/status')
    } catch (e) {
      /* 网络瞬时错误，继续轮询 */
    }
    if (stopPoll) return
    if (!s) {
      pollTimer = setTimeout(tick, 3000)
      return
    }
    if (s.running && s.camera_ok) {
      starting.value = false
      return
    }
    if (s.running && s.loading) {
      pollTimer = setTimeout(tick, 3000)
      return
    }
    if (s.running) {
      starting.value = false
      camMsg.value = '摄像头未就绪：' + (s.error || '未知错误')
      return
    }
    starting.value = false
    camMsg.value = '采集进程未启动，请查看服务端日志'
  }
  tick()
}

async function toggleCapture() {
  if (captureBusy.value) return
  camMsg.value = ''
  busy.value = true
  try {
    if (workerRunning.value || forceStopped.value) {
      await api.post('/api/camera/stop')
      starting.value = false
      forceStopped.value = true
    } else {
      await api.post('/api/camera/start')
      forceStopped.value = false
      starting.value = true
      pollStatus()
    }
  } catch (e) {
    camMsg.value = e.message || '操作失败'
  } finally {
    busy.value = false
  }
}

onBeforeUnmount(() => {
  stopPoll = true
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<template>
  <div class="panel panel-identity">
    <div class="panel-title">
      <span>身份识别</span>
      <span class="hint">IDENTITY</span>
    </div>
    <div class="panel-body identity-body">
      <div class="identity-row">
        <span class="identity-name mono">{{ name }}</span>
        <span class="identity-tag" :class="stale ? 'stale' : isUnknown ? 'unknown' : 'known'">
          {{ stale ? 'STALE' : isUnknown ? 'UNKNOWN' : 'KNOWN' }}
        </span>
        <span class="identity-conf mono">
          {{ confidence != null ? 'CONF ' + (confidence * 100).toFixed(0) + '%' : '--' }}
        </span>
        <button
          class="btn btn-capture"
          :class="{ stop: workerRunning && !starting }"
          :disabled="captureBusy"
          type="button"
          @click="toggleCapture"
        >
          {{ captureLabel }}
        </button>
      </div>
      <p v-if="camMsg" class="identity-msg mono">{{ camMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.identity-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  overflow: hidden;
}

.identity-row {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.identity-name {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.06em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.identity-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: 0.1em;
  border: 1px solid;
  flex: 0 0 auto;
}

.identity-tag.known {
  color: var(--ok);
  border-color: rgba(61, 220, 151, 0.4);
}

.identity-tag.unknown {
  color: var(--warn);
  border-color: rgba(245, 180, 85, 0.4);
}

.identity-tag.stale {
  color: var(--text-dim);
  border-color: var(--panel-border);
}

.identity-conf {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-dim);
  flex: 0 0 auto;
}

.identity-msg {
  font-size: 11px;
  color: var(--warn);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-capture {
  padding: 5px 12px;
  font-size: 12px;
  background: rgba(34, 211, 198, 0.12);
  border-color: rgba(34, 211, 198, 0.4);
  color: var(--accent);
  border-radius: 6px;
  cursor: pointer;
  flex: 0 0 auto;
  transition: background 0.15s, border-color 0.15s;
}

.btn-capture:hover:not(:disabled) {
  background: rgba(34, 211, 198, 0.2);
}

.btn-capture.stop {
  background: rgba(242, 95, 92, 0.12);
  border-color: rgba(242, 95, 92, 0.4);
  color: var(--danger);
}

.btn-capture:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
