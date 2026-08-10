<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useCaptureSession } from '../composables/useCaptureSession'

const { running, analyser, voice } = useCaptureSession()

const canvasEl = ref(null)
let raf = null

function draw() {
  raf = null
  const canvas = canvasEl.value
  const analyserNode = analyser.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  // 以 CSS 布局尺寸为基准；canvas.width/height 是 backing-store（设备像素），不能直接拿来乘 dpr。
  const dpr = window.devicePixelRatio || 1
  const cssW = canvas.clientWidth
  const cssH = canvas.clientHeight
  if (cssW > 0 && cssH > 0) {
    const bw = Math.round(cssW * dpr)
    const bh = Math.round(cssH * dpr)
    if (canvas.width !== bw || canvas.height !== bh) {
      canvas.width = bw
      canvas.height = bh
    }
    // 每帧先复位再应用 dpr，避免缩放累积
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, cssW, cssH)

    const mid = cssH / 2
    const n = 96
    if (analyserNode) {
      const data = new Uint8Array(analyserNode.frequencyBinCount)
      analyserNode.getByteTimeDomainData(data)
      ctx.strokeStyle = '#22d3c6'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      const step = Math.floor(data.length / n) || 1
      for (let i = 0; i < n; i++) {
        const v = (data[i * step] - 128) / 128
        const x = (i / (n - 1)) * cssW
        const y = mid + v * (mid - 4)
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
    } else {
      ctx.strokeStyle = 'rgba(64, 200, 190, 0.25)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, mid)
      ctx.lineTo(cssW, mid)
      ctx.stroke()
    }
  }

  if (running.value) raf = requestAnimationFrame(draw)
}

watch([running, analyser], () => {
  if (running.value && !raf) draw()
})

onMounted(() => {
  if (running.value) draw()
})

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
})
</script>

<template>
  <div class="panel panel-voice">
    <div class="panel-title">
      <span>声纹</span>
      <span class="hint">VOICE</span>
    </div>
    <div class="panel-body voice-body">
      <div class="voice-status">
        <span class="dot" :class="voice.speaking ? 'ok' : 'off'"></span>
        <span class="voice-label mono">{{ voice.speaking ? 'SPEAKING' : 'SILENCE' }}</span>
        <span class="voice-level mono">{{ (voice.level * 100).toFixed(0) }}</span>
      </div>
      <canvas ref="canvasEl" class="voice-canvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.voice-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.voice-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.voice-label {
  font-size: 11px;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}

.voice-level {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-dim);
}

.voice-canvas {
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
  min-height: 0;
  /* 不透明底色兜底：任何 resize 重置画布都不会白闪 */
  background: var(--bg-1);
}
</style>
