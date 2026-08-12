<script setup>
import { ref, watch } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'
import { api } from '../api/client'
import ReportView from './ReportView.vue'

const { running, sessionStart, sessionEnd, identity } = useCaptureSession()

const show = ref(false)
const busy = ref(false)
const err = ref('')
const report = ref(null)

watch(running, (now, prev) => {
  if (prev === true && now === false && sessionStart.value) {
    show.value = true
    err.value = ''
  }
})

async function generate() {
  busy.value = true
  err.value = ''
  try {
    const r = await api.post('/api/report/generate', {
      start: sessionStart.value?.toISOString(),
      end: sessionEnd.value?.toISOString(),
      person_name: identity.value?.available ? identity.value.person_name : 'unknown',
    })
    if (r.error) {
      err.value = r.error
    } else {
      report.value = r
      show.value = false
    }
  } catch (e) {
    err.value = e.message || '报告生成失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="prompt-overlay">
      <div class="prompt-box">
        <h3 class="prompt-title">本次监测已结束</h3>
        <p class="prompt-text">是否生成正式监测报告？</p>
        <p v-if="err" class="prompt-err mono">{{ err }}</p>
        <div class="prompt-actions">
          <button class="btn ghost" type="button" @click="show = false">暂不生成</button>
          <button class="btn primary" type="button" :disabled="busy" @click="generate">
            {{ busy ? '生成中…' : '生成报告' }}
          </button>
        </div>
      </div>
    </div>

    <ReportView v-if="report" :report="report" @close="report = null" />
  </Teleport>
</template>

<style scoped>
.prompt-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(7, 11, 18, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
}

.prompt-box {
  width: 360px;
  max-width: 90vw;
  background: var(--bg-1);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}

.prompt-title {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--text);
}

.prompt-text {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-dim);
}

.prompt-err {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--warn);
}

.prompt-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 8px 18px;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
}

.btn.ghost:hover {
  background: rgba(255, 255, 255, 0.06);
}

.btn.primary {
  background: rgba(34, 211, 198, 0.12);
  border-color: rgba(34, 211, 198, 0.4);
  color: var(--accent);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
