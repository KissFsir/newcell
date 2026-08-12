<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const c = computed(() => props.report.content || {})
const isAI = computed(() => props.report.mode === 'ai')

function fmtTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const emotionText = computed(() => {
  const counts = c.value.emotion_counts || {}
  const items = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (!items.length) return '（未采集到有效表情数据）'
  return items.map(([k, v]) => `${k} ${v} 次`).join('；')
})

const trendText = computed(() => {
  const t = c.value.trend || []
  if (!t.length) return '（无）'
  // 压缩连续重复（neutral,neutral,fear → neutral,fear），顿号连接，避免箭头与超长序列
  const compressed = []
  for (const e of t) {
    if (compressed[compressed.length - 1] !== e) compressed.push(e)
  }
  const MAX = 8
  return compressed.slice(0, MAX).join('、') + (compressed.length > MAX ? '等' : '')
})

const physioText = computed(() => {
  const p = c.value.physio || {}
  const parts = []
  if (p.temp) parts.push(`体温均值 ${p.temp[0].toFixed(1)}°C（${p.temp[1].toFixed(1)}~${p.temp[2].toFixed(1)}）`)
  if (p.pulse) parts.push(`脉搏均值 ${p.pulse[0].toFixed(1)}（${p.pulse[1].toFixed(1)}~${p.pulse[2].toFixed(1)}）`)
  if (p.gsr) parts.push(`皮电均值 ${Math.round(p.gsr[0])}（${Math.round(p.gsr[1])}~${Math.round(p.gsr[2])}）`)
  return parts.length ? parts.join('；') : '（未采集到生理数据）'
})

const identityText = computed(() => {
  const extras = [c.value.gender, c.value.major].filter(Boolean)
  return c.value.person + (extras.length ? `（${extras.join('，')}）` : '')
})
</script>

<template>
  <Teleport to="body">
    <div class="report-overlay">
      <div class="report-toolbar">
        <button type="button" class="btn" @click="emit('close')">关闭</button>
        <a class="btn primary" :href="`/api/reports/${props.report.id}/pdf`">下载 PDF</a>
      </div>

      <div class="report-scroll">
        <article class="report-sheet">
          <header class="report-head">
            <h1 class="report-title">情绪状态监测报告</h1>
            <p class="report-meta mono">报告编号 NC-{{ String(props.report.id).padStart(4, '0') }} · 生成时间 {{ fmtTime(props.report.created_at) }}</p>
            <hr />
          </header>

          <!-- 全 AI 模式 -->
          <section v-if="isAI" class="report-body-text">
            <p class="ai-text">{{ c.text }}</p>
          </section>

          <!-- 结构化模式 -->
          <section v-else class="report-body">
            <div class="report-section">
              <h2 class="section-title">一、监测对象</h2>
              <table class="info-table">
                <tbody>
                  <tr><td class="label">姓名</td><td>{{ identityText }}</td></tr>
                  <tr><td class="label">监测时间</td><td>{{ fmtTime(c.start) }} ~ {{ fmtTime(c.end) }}</td></tr>
                </tbody>
              </table>
            </div>

            <div class="report-section">
              <h2 class="section-title">二、情绪状态分析</h2>
              <table class="info-table">
                <tbody>
                  <tr><td class="label">主情绪分布</td><td>{{ emotionText }}</td></tr>
                  <tr><td class="label">情绪变化</td><td>{{ trendText }}</td></tr>
                </tbody>
              </table>
            </div>

            <div class="report-section">
              <h2 class="section-title">三、语音内容摘要</h2>
              <p class="body-text">{{ c.transcript || '（未采集到有效语音）' }}</p>
            </div>

            <div class="report-section">
              <h2 class="section-title">四、生理指标</h2>
              <p class="body-text">{{ physioText }}</p>
            </div>

            <div class="report-section">
              <h2 class="section-title">五、综合结论与建议</h2>
              <p class="body-text conclusion">{{ c.conclusion || '（结论生成中）' }}</p>
            </div>
          </section>

          <footer class="report-foot">
            <p>新元多模态情绪识别系统</p>
            <p>{{ new Date().toLocaleDateString('zh-CN') }}</p>
          </footer>
        </article>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.report-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(7, 11, 18, 0.92);
  display: flex;
  flex-direction: column;
}

.report-toolbar {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 16px;
}

.btn {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 8px 18px;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn.primary {
  background: rgba(34, 211, 198, 0.12);
  border-color: rgba(34, 211, 198, 0.4);
  color: var(--accent);
}

.report-scroll {
  flex: 1 1 auto;
  overflow: auto;
  padding: 0 20px 40px;
}

.report-sheet {
  max-width: 820px;
  margin: 0 auto;
  background: #fff;
  color: #1a1a1a;
  padding: 48px 56px;
  border-radius: 4px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
}

.report-title {
  text-align: center;
  font-size: 24px;
  letter-spacing: 0.2em;
  margin: 0 0 10px;
  color: #111;
}

.report-meta {
  text-align: center;
  font-size: 11px;
  color: #666;
  margin: 0 0 16px;
}

.report-body,
.report-body-text {
  margin-top: 20px;
}

.report-section {
  margin-bottom: 22px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #111;
  border-left: 3px solid #22a6a0;
  padding-left: 10px;
  margin: 0 0 10px;
}

.info-table {
  width: 100%;
  border-collapse: collapse;
}

.info-table td {
  padding: 6px 10px;
  font-size: 13px;
  vertical-align: top;
  border-bottom: 1px solid #eee;
}

.info-table .label {
  width: 110px;
  color: #666;
  font-size: 12px;
}

.body-text {
  font-size: 14px;
  line-height: 1.9;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.conclusion {
  padding: 12px 14px;
  background: #f7faf9;
  border: 1px solid #e6efee;
  border-radius: 4px;
}

.ai-text {
  font-size: 14px;
  line-height: 2;
  white-space: pre-wrap;
  word-break: break-word;
}

.report-foot {
  margin-top: 32px;
  text-align: right;
  color: #555;
  font-size: 12px;
}

.report-foot p {
  margin: 2px 0;
}
</style>

<style>
/* 打印：只显示报告纸 */
@media print {
  body * {
    visibility: hidden;
  }
  .report-sheet,
  .report-sheet * {
    visibility: visible;
  }
  .report-sheet {
    position: absolute;
    left: 0;
    top: 0;
    max-width: none;
    box-shadow: none;
    border-radius: 0;
    padding: 40px 48px;
  }
  .report-overlay {
    background: #fff;
  }
  .report-toolbar {
    display: none;
  }
}
</style>
