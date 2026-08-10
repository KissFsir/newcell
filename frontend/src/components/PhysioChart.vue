<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api/client'

const data = ref({ status: { a: {}, b: {} }, samples: [], latest: null })
const err = ref('')
const canvasEl = ref(null)
let timer = null

const temp = computed(() => data.value.latest?.temp ?? null)
const hum = computed(() => data.value.latest?.humidity ?? null)
const gsr = computed(() => data.value.latest?.gsr ?? null)
const aOn = computed(() => !!data.value.status.a?.connected)
const bOn = computed(() => !!data.value.status.b?.connected)
const aRate = computed(() => data.value.status.a?.rate ?? 0)
const bRate = computed(() => data.value.status.b?.rate ?? 0)

async function poll() {
  try {
    data.value = await api.get('/api/physio/latest')
  } catch (e) {
    err.value = e.message || '生理数据获取失败'
  }
}

function draw() {
  const canvas = canvasEl.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const cssW = canvas.clientWidth
  const cssH = canvas.clientHeight
  if (!cssW || !cssH) return
  const bw = Math.round(cssW * dpr)
  const bh = Math.round(cssH * dpr)
  if (canvas.width !== bw || canvas.height !== bh) {
    canvas.width = bw
    canvas.height = bh
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, cssW, cssH)

  const pulses = data.value.samples.filter((s) => s.port === 'a').map((s) => s.pulse)
  const mid = cssH / 2
  if (pulses.length > 1) {
    const min = Math.min(...pulses)
    const max = Math.max(...pulses)
    const span = max - min || 1
    ctx.strokeStyle = '#22d3c6'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    for (let i = 0; i < pulses.length; i++) {
      const x = (i / (pulses.length - 1)) * cssW
      const y = cssH - ((pulses[i] - min) / span) * cssH * 0.9 - cssH * 0.05
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

watch(data, draw)
window.addEventListener('resize', draw)

onMounted(() => {
  poll()
  timer = setInterval(poll, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', draw)
})
</script>

<template>
  <div class="panel panel-physio">
    <div class="panel-title">
      <span>生理信号</span>
      <span class="hint">PHYSIO</span>
    </div>
    <div class="panel-body physio-body">
      <div class="physio-stats">
        <div class="stat">
          <span class="stat-label">体温</span>
          <span class="stat-value mono">{{ temp != null ? temp.toFixed(1) + '°C' : '--' }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">湿度</span>
          <span class="stat-value mono">{{ hum != null ? Math.round(hum) + '%' : '--' }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">皮电</span>
          <span class="stat-value mono">{{ gsr != null ? Math.round(gsr) : '--' }}</span>
        </div>
      </div>

      <div class="wave-wrap">
        <span class="wave-label">脉搏波形</span>
        <canvas ref="canvasEl" class="physio-canvas"></canvas>
      </div>

      <div class="physio-status">
        <span class="status-dot" :class="aOn ? 'on' : 'off'"></span>
        <span class="mono">A {{ aOn ? '已连接 · ' + aRate + 'Hz' : '未连接' }}</span>
        <span class="status-dot" :class="bOn ? 'on' : 'off'"></span>
        <span class="mono">B {{ bOn ? '已连接 · ' + bRate + 'Hz' : '未连接' }}</span>
      </div>
      <p v-if="err" class="physio-err mono">{{ err }}</p>
    </div>
  </div>
</template>

<style scoped>
.physio-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.physio-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  flex: 0 0 auto;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-label {
  font-size: 10px;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}

.stat-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wave-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1 1 auto;
  min-height: 0;
}

.wave-label {
  font-size: 10px;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}

.physio-canvas {
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
  min-height: 0;
  background: var(--bg-1);
  border-radius: 6px;
}

.physio-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-dim);
  flex: 0 0 auto;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.status-dot.on {
  background: var(--ok);
  box-shadow: 0 0 6px var(--ok);
}

.status-dot.off {
  background: var(--text-dim);
}

.physio-err {
  margin: 0;
  font-size: 11px;
  color: var(--warn);
}
</style>
