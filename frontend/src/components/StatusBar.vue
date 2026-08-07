<script setup>
import { computed } from 'vue'
import { useNow } from '@vueuse/core'
import { useSnapshotStream } from '../composables/useSnapshotStream'

const { snapshot } = useSnapshotStream()
const now = useNow({ interval: 1000 })

const status = computed(() => snapshot.value?.status || null)

const workerState = computed(() => {
  if (!status.value) return 'off'
  return status.value.worker_running ? 'ok' : 'warn'
})

const cameraState = computed(() => {
  if (!status.value || !status.value.worker_running) return 'off'
  return status.value.camera_ok ? 'ok' : 'warn'
})

const sseState = computed(() => (snapshot.value ? 'ok' : 'off'))

const timeStr = computed(() =>
  now.value.toLocaleTimeString('zh-CN', { hour12: false })
)
</script>

<template>
  <footer class="statusbar mono">
    <span class="status-item">
      <span class="dot" :class="'dot-' + sseState"></span>LINK {{ sseState }}
    </span>
    <span class="status-item">
      <span class="dot" :class="'dot-' + workerState"></span>WORKER {{ workerState }}
    </span>
    <span class="status-item">
      <span class="dot" :class="'dot-' + cameraState"></span>CAMERA {{ cameraState }}
    </span>
    <span class="status-item">
      UPDATE {{ status?.last_update_seconds ?? '--' }}s
    </span>
    <span class="status-spacer"></span>
    <span>{{ timeStr }}</span>
  </footer>
</template>
