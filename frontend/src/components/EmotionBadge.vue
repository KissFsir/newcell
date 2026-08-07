<script setup>
import { computed } from 'vue'
import { useSnapshotStream } from '../composables/useSnapshotStream'
import { EMOTION_ZH, EMOTION_COLOR } from '../constants/emotions'

const { snapshot } = useSnapshotStream()

const expr = computed(() => snapshot.value?.expression)
const dominant = computed(() => {
  if (!expr.value?.available) return null
  return expr.value.dominant_emotion
})
const confidence = computed(() => expr.value?.available ? expr.value.confidence : null)
const zh = computed(() => (dominant.value ? EMOTION_ZH[dominant.value] || dominant.value : '等待数据'))
const color = computed(() => (dominant.value ? EMOTION_COLOR[dominant.value] : 'var(--text-dim)'))
</script>

<template>
  <div class="panel emotion-badge">
    <div class="panel-body badge-body">
      <div class="badge-left">
        <span class="badge-label">当前主情绪</span>
        <span class="badge-value mono" :style="{ color }">{{ zh }}</span>
      </div>
      <div class="badge-right mono">
        <template v-if="confidence != null">
          <span class="badge-stat" :style="{ color }">{{ dominant }}</span>
          <span class="badge-stat">CONF {{ (confidence * 100).toFixed(0) }}%</span>
        </template>
        <span v-else class="badge-stat">NO DATA</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.badge-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 18px;
  overflow: hidden;
}

.badge-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.badge-label {
  font-size: 12px;
  letter-spacing: 0.2em;
  color: var(--text-dim);
}

.badge-value {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1;
}

.badge-right {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: var(--text-dim);
  letter-spacing: 0.1em;
}
</style>
