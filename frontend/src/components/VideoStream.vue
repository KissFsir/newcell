<script setup>
import { computed, ref, watch } from 'vue'
import { useSnapshotStream } from '../composables/useSnapshotStream'

const { snapshot } = useSnapshotStream()
const offline = ref(false)

const status = computed(() => snapshot.value?.status || null)
const live = computed(() => !!status.value?.worker_running && !!status.value?.camera_ok)
const loading = computed(() => !!status.value?.worker_running && !status.value?.camera_ok)

// worker 重新就绪时自动重连 MJPEG
watch(live, (on) => {
  if (on) offline.value = false
})

function onError() {
  offline.value = true
}

const stubText = computed(() => {
  if (loading.value) return '采集中…'
  if (offline.value) return '预览中断'
  return 'CAMERA OFF'
})
</script>

<template>
  <div class="panel panel-video">
    <div class="panel-title">
      <span>摄像头预览</span>
      <span class="hint">LIVE</span>
    </div>
    <div class="panel-body video-body">
      <img
        v-if="live && !offline"
        :src="'/api/video/stream'"
        alt="camera"
        class="video-frame"
        @error="onError"
      />
      <div v-else class="stub">{{ stubText }}</div>
    </div>
  </div>
</template>

<style scoped>
.video-body {
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
  background: #000;
}
</style>
