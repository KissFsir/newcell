<script setup>
import { computed } from 'vue'
import { useNow } from '@vueuse/core'
import { useCaptureSession } from '../composables/useCaptureSession'

const { running, modelState } = useCaptureSession()
const now = useNow({ interval: 1000 })

const modelStatus = computed(() => {
  if (modelState.value === 'ready') return 'ok'
  if (modelState.value === 'loading') return 'warn'
  if (modelState.value === 'error') return 'danger'
  return 'off'
})
const cameraStatus = computed(() => (running.value ? 'ok' : 'off'))

const timeStr = computed(() =>
  now.value.toLocaleTimeString('zh-CN', { hour12: false })
)
</script>

<template>
  <footer class="statusbar mono">
    <span class="status-item">
      <span class="dot" :class="'dot-' + cameraStatus"></span>CAMERA {{ cameraStatus }}
    </span>
    <span class="status-item">
      <span class="dot" :class="'dot-' + modelStatus"></span>MODEL {{ modelState }}
    </span>
    <span class="status-spacer"></span>
    <span>{{ timeStr }}</span>
  </footer>
</template>
