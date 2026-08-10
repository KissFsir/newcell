<script setup>
import { computed } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'

const { transcriptItems, interimText, mode, speechSupported } = useCaptureSession()

const empty = computed(() => transcriptItems.value.length === 0)
const hint = computed(() => (mode.value === 'api' ? 'WEB API' : 'LOCAL'))
const apiUnsupported = computed(() => mode.value === 'api' && !speechSupported)
</script>

<template>
  <div class="panel panel-transcript">
    <div class="panel-title">
      <span>中文实时转录</span>
      <span class="hint" :class="{ warn: apiUnsupported }">{{ apiUnsupported ? 'UNSUPPORTED' : hint }}</span>
    </div>
    <div class="panel-body transcript-body">
      <p v-if="apiUnsupported" class="transcript-msg mono">当前浏览器不支持 Web Speech API（Chrome/Edge/Safari 可用），请在「设置」切换回本地模型。</p>
      <div v-else-if="interimText" class="transcript-item interim">
        <span class="transcript-time mono">LIVE</span>
        <span class="transcript-text">{{ interimText }}</span>
      </div>
      <ul v-if="!empty" class="transcript-list">
        <li v-for="(item, i) in transcriptItems" :key="i" class="transcript-item">
          <span class="transcript-time mono">{{ item.timeLabel }}</span>
          <span class="transcript-text">{{ item.text }}</span>
        </li>
      </ul>
      <div v-if="empty && !interimText && !apiUnsupported" class="stub">NO SPEECH</div>
    </div>
  </div>
</template>

<style scoped>
.transcript-body {
  overflow-y: auto;
}

.transcript-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.transcript-item {
  display: flex;
  gap: 10px;
  align-items: baseline;
  font-size: 13px;
  line-height: 1.5;
}

.transcript-time {
  flex: 0 0 auto;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.05em;
}

.transcript-text {
  color: var(--text);
  word-break: break-word;
}

.transcript-item.interim .transcript-time {
  color: var(--accent);
}

.transcript-item.interim .transcript-text {
  color: var(--text-dim);
  font-style: italic;
}

.hint.warn {
  color: var(--warn);
}

.transcript-msg {
  margin: 0;
  font-size: 12px;
  color: var(--warn);
}
</style>
