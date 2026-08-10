<script setup>
import { computed } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'

const { running, modelState, setVideoEl } = useCaptureSession()

const live = computed(() => running.value)
const loading = computed(() => running.value && modelState.value !== 'ready')
</script>

<template>
  <div class="panel panel-video">
    <div class="panel-title">
      <span>摄像头预览</span>
      <span class="hint">LIVE</span>
    </div>
    <div class="panel-body video-body">
      <video
        v-if="live"
        :ref="setVideoEl"
        autoplay
        muted
        playsinline
        class="video-frame"
      ></video>
      <div v-else class="stub">CAMERA OFF</div>
      <div v-if="loading" class="video-overlay mono">模型加载中…</div>
    </div>
  </div>
</template>

<style scoped>
.video-body {
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
  background: #000;
}

.video-overlay {
  position: absolute;
  inset: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  letter-spacing: 0.15em;
  color: var(--accent);
  background: rgba(7, 11, 18, 0.55);
  border-radius: 6px;
  pointer-events: none;
}
</style>
