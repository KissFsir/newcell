<script setup>
import { computed, onMounted, ref } from 'vue'
import { useTranscriptionMode, isWebSpeechSupported } from '../composables/useTranscriptionMode'
import { api } from '../api/client'

const { mode } = useTranscriptionMode()
const speechSupported = isWebSpeechSupported()

const options = [
  {
    key: 'local',
    label: '本地模型',
    desc: '浏览器采集音频 → 上传本机后端 whisper 转录，可离线、不占浏览器网络。',
  },
  {
    key: 'api',
    label: 'Web Speech API',
    desc: '浏览器内置谷歌识别，识别在浏览器内完成，需麦克风权限 + 网络，不占用本地模型。',
  },
]
const activeDesc = computed(() => options.find((o) => o.key === mode.value)?.desc || '')

// ---- AI 情感洞察（LLM）配置 ----
const llmProviders = [
  { key: 'ollama', label: 'Ollama（本地）' },
  { key: 'deepseek', label: 'DeepSeek API' },
]
const llm = ref({ provider: 'ollama', ollama_model: 'qwen2.5:7b', deepseek_api_key: '' })
const llmBusy = ref(false)
const llmMsg = ref('')
const llmMsgType = ref('')

async function loadLlm() {
  try {
    const data = await api.get('/api/settings/llm')
    llm.value = { ...llm.value, ...data }
  } catch (e) {
    // 后端不可用则保持默认
  }
}

async function saveLlm() {
  llmBusy.value = true
  llmMsg.value = ''
  try {
    llm.value = await api.put('/api/settings/llm', llm.value)
    llmMsg.value = '已保存'
    llmMsgType.value = 'ok'
  } catch (e) {
    llmMsg.value = e.message || '保存失败'
    llmMsgType.value = 'danger'
  } finally {
    llmBusy.value = false
  }
}

// ---- 生理数据采集（串口） ----
const serial = ref({ enabled: false, port_a: 'COM6', port_b: 'COM5', baudrate: 115200 })
const serialPorts = ref([])
const serialBusy = ref(false)
const serialMsg = ref('')
const serialMsgType = ref('')

async function loadSerial() {
  try {
    const data = await api.get('/api/settings/serial')
    serial.value = { ...serial.value, ...data }
  } catch (e) { /* 后端不可用则保持默认 */ }
  try {
    const d = await api.get('/api/serial/ports')
    serialPorts.value = d.ports || []
  } catch (e) { /* 忽略 */ }
}

async function saveSerial() {
  serialBusy.value = true
  serialMsg.value = ''
  try {
    serial.value = await api.put('/api/settings/serial', serial.value)
    serialMsg.value = '已保存'
    serialMsgType.value = 'ok'
  } catch (e) {
    serialMsg.value = e.message || '保存失败'
    serialMsgType.value = 'danger'
  } finally {
    serialBusy.value = false
  }
}

onMounted(() => {
  loadLlm()
  loadSerial()
})
</script>

<template>
  <div class="panel settings-panel">
    <div class="panel-title">
      <span>设置</span>
      <span class="hint">SETTINGS</span>
    </div>
    <div class="panel-body settings-body">
      <section class="settings-group">
        <h3 class="settings-label">语音转录方式</h3>
        <div class="segmented" role="radiogroup" aria-label="语音转录方式">
          <button
            v-for="opt in options"
            :key="opt.key"
            type="button"
            class="seg-item mono"
            :class="{ active: mode === opt.key }"
            :aria-pressed="mode === opt.key"
            @click="mode = opt.key"
          >
            {{ opt.label }}
          </button>
        </div>
        <p class="settings-desc mono">{{ activeDesc }}</p>
        <p v-if="mode === 'api' && !speechSupported" class="settings-warn mono">
          当前浏览器不支持 Web Speech API（Chrome/Edge/Safari 可用），转录将无法工作，请改用本地模型。
        </p>
      </section>

      <section class="settings-group">
        <h3 class="settings-label">AI 情感洞察</h3>
        <div class="segmented" role="radiogroup" aria-label="AI 分析来源">
          <button
            v-for="p in llmProviders"
            :key="p.key"
            type="button"
            class="seg-item mono"
            :class="{ active: llm.provider === p.key }"
            :aria-pressed="llm.provider === p.key"
            @click="llm.provider = p.key"
          >
            {{ p.label }}
          </button>
        </div>

        <template v-if="llm.provider === 'ollama'">
          <label class="field">
            <span class="field-label">Ollama 模型名</span>
            <input v-model="llm.ollama_model" class="input mono" placeholder="qwen2.5:7b" maxlength="128" />
            <span class="field-note mono">需与 <span class="mono">ollama list</span> 里的名称一致</span>
          </label>
        </template>
        <template v-else>
          <label class="field">
            <span class="field-label">DeepSeek API Key</span>
            <input
              v-model="llm.deepseek_api_key"
              type="password"
              class="input mono"
              placeholder="sk-…"
              autocomplete="off"
            />
            <span class="field-note mono">模型固定 deepseek-v4-flash · 接口 https://api.deepseek.com</span>
          </label>
        </template>

        <div class="form-actions">
          <button class="btn primary" :disabled="llmBusy" @click="saveLlm">
            {{ llmBusy ? '保存中…' : '保存' }}
          </button>
          <span v-if="llmMsg" class="form-msg" :class="llmMsgType">{{ llmMsg }}</span>
        </div>
      </section>

      <section class="settings-group">
        <h3 class="settings-label">生理数据采集</h3>
        <div class="field">
          <label class="switch-row">
            <span class="field-label">开启串口采集</span>
            <input v-model="serial.enabled" type="checkbox" class="switch" />
          </label>
        </div>
        <div class="field">
          <span class="field-label">端口 A（温湿度 + 脉搏）</span>
          <input
            v-model="serial.port_a"
            class="input mono"
            placeholder="COM6 / /dev/cu.usbserial-XXX"
            list="serial-ports"
          />
        </div>
        <div class="field">
          <span class="field-label">端口 B（皮电）</span>
          <input
            v-model="serial.port_b"
            class="input mono"
            placeholder="COM5 / /dev/cu.usbserial-XXX"
            list="serial-ports"
          />
        </div>
        <div class="field">
          <span class="field-label">波特率</span>
          <input v-model.number="serial.baudrate" type="number" class="input mono" />
        </div>
        <datalist id="serial-ports">
          <option v-for="p in serialPorts" :key="p.device" :value="p.device">
            {{ p.description }}
          </option>
        </datalist>
        <p v-if="serialPorts.length === 0" class="field-note mono">
          未检测到可用串口（直连板子后刷新页面）
        </p>
        <div class="form-actions">
          <button class="btn primary" :disabled="serialBusy" @click="saveSerial">
            {{ serialBusy ? '保存中…' : '保存' }}
          </button>
          <span v-if="serialMsg" class="form-msg" :class="serialMsgType">{{ serialMsg }}</span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-panel {
  max-width: 720px;
  margin: var(--gap) auto 0;
}

.settings-body {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.settings-label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  color: var(--text-dim);
  text-transform: uppercase;
}

.segmented {
  display: inline-flex;
  align-self: flex-start;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  overflow: hidden;
}

.seg-item {
  padding: 8px 18px;
  background: transparent;
  border: none;
  color: var(--text-dim);
  font-size: 13px;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.seg-item:hover {
  color: var(--text);
}

.seg-item.active {
  background: rgba(34, 211, 198, 0.12);
  color: var(--accent);
}

.settings-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-dim);
}

.settings-warn {
  margin: 0;
  font-size: 12px;
  color: var(--warn);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--text-dim);
  text-transform: uppercase;
}

.field-note {
  font-size: 11px;
  color: var(--text-dim);
}

.input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  color: var(--text);
  padding: 8px 10px;
  font-size: 14px;
  outline: none;
}

.input:focus {
  border-color: var(--accent);
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch {
  width: 42px;
  height: 23px;
  border-radius: 12px;
  background: var(--text-dim);
  position: relative;
  cursor: pointer;
  appearance: none;
  transition: background 0.15s;
  flex: 0 0 auto;
}

.switch::after {
  content: '';
  position: absolute;
  top: 2.5px;
  left: 2.5px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.15s;
}

.switch:checked {
  background: var(--accent);
}

.switch:checked::after {
  transform: translateX(19px);
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.btn {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 8px 18px;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.btn.primary {
  background: rgba(34, 211, 198, 0.12);
  border-color: rgba(34, 211, 198, 0.4);
  color: var(--accent);
}

.btn.primary:hover:not(:disabled) {
  background: rgba(34, 211, 198, 0.2);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-msg {
  font-size: 13px;
  margin: 0;
}

.form-msg.ok {
  color: var(--ok);
}

.form-msg.danger {
  color: var(--danger);
}
</style>
