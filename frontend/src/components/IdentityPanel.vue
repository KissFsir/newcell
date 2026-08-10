<script setup>
import { computed } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'

const { identity } = useCaptureSession()

const name = computed(() => (identity.value?.available ? identity.value.person_name : 'NO FACE'))
const confidence = computed(() => identity.value?.confidence ?? null)
const isUnknown = computed(() => identity.value?.is_unknown ?? true)
const info = computed(() => {
  if (!identity.value?.available) return null
  return {
    gender: identity.value.gender || '--',
    student_no: identity.value.student_no || '--',
    major: identity.value.major || '--',
  }
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
        <span class="identity-tag" :class="isUnknown ? 'unknown' : 'known'">
          {{ isUnknown ? 'UNKNOWN' : 'KNOWN' }}
        </span>
        <span class="identity-conf mono">
          {{ confidence != null ? 'CONF ' + (confidence * 100).toFixed(0) + '%' : '--' }}
        </span>
      </div>

      <div v-if="info" class="identity-info">
        <div class="info-item">
          <span class="info-label mono">性别</span>
          <span class="info-value mono">{{ info.gender }}</span>
        </div>
        <div class="info-item">
          <span class="info-label mono">学号</span>
          <span class="info-value mono">{{ info.student_no }}</span>
        </div>
        <div class="info-item">
          <span class="info-label mono">专业</span>
          <span class="info-value mono">{{ info.major }}</span>
        </div>
      </div>
      <div v-else class="stub identity-stub">NO IDENTITY DATA</div>
    </div>
  </div>
</template>

<style scoped>
.identity-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  overflow: hidden;
}

.identity-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.identity-name {
  font-size: 20px;
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

.identity-conf {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-dim);
  flex: 0 0 auto;
}

.identity-info {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  border-top: 1px solid var(--panel-border);
  padding-top: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.info-label {
  font-size: 10px;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}

.info-value {
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.identity-stub {
  min-height: 40px;
}
</style>
