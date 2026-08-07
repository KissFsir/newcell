<script setup>
import { computed } from 'vue'
import { useSnapshotStream } from '../composables/useSnapshotStream'
import { EMOTION_LABELS, EMOTION_ZH, EMOTION_COLOR } from '../constants/emotions'

const { snapshot } = useSnapshotStream()

const probs = computed(() => {
  const expr = snapshot.value?.expression
  if (!expr?.available) return null
  return expr.probabilities
})

const bars = computed(() => {
  if (!probs.value) return []
  return EMOTION_LABELS.map((k) => ({
    key: k,
    zh: EMOTION_ZH[k],
    color: EMOTION_COLOR[k],
    value: probs.value[k] ?? 0,
  }))
})
</script>

<template>
  <div class="panel panel-expression">
    <div class="panel-title">
      <span>面部表情</span>
      <span class="hint">FACIAL</span>
    </div>
    <div class="panel-body">
      <div v-if="bars.length === 0" class="stub">WAITING FOR DATA</div>
      <div v-else class="bars">
        <div v-for="b in bars" :key="b.key" class="bar-row">
          <span class="bar-label">{{ b.zh }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: (b.value * 100).toFixed(1) + '%', background: b.color }"></div>
          </div>
          <span class="bar-value mono">{{ (b.value * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  justify-content: space-evenly;
}

.bar-row {
  display: grid;
  grid-template-columns: 44px 1fr 42px;
  align-items: center;
  gap: 10px;
}

.bar-label {
  font-size: 13px;
  color: var(--text);
  text-align: right;
}

.bar-track {
  height: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 5px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s ease;
  box-shadow: 0 0 6px rgba(34, 211, 198, 0.3);
}

.bar-value {
  font-size: 12px;
  color: var(--text-dim);
  text-align: right;
}
</style>
