<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'

const name = ref('')
const file = ref(null)
const busy = ref(false)
const msg = ref('')
const msgType = ref('')
const faces = ref([])

const FACE_ERRORS = {
  no_face_detected: '未检测到人脸，请正对镜头重试',
  invalid_image: '图片无效，请重新拍摄或上传',
  name_and_file_required: '请填写姓名并拍照或上传照片',
  method_not_allowed: '请求方式错误',
}

// 摄像头采集
const camActive = ref(false)
const camError = ref('')
const capturedImg = ref('') // 已采集照片 dataURL
const videoRef = ref(null)
const canvasRef = ref(null)
const fileInputRef = ref(null)
let stream = null

async function loadFaces() {
  const data = await api.get('/api/faces')
  faces.value = data.faces || []
}

function onFile(e) {
  file.value = e.target.files?.[0] || null
  capturedImg.value = '' // 选择文件后清掉已采集照片
}

async function startCam() {
  camError.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    camError.value = '当前浏览器不支持摄像头采集'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    })
    camActive.value = true
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      await videoRef.value.play()
    }
  } catch (e) {
    camError.value =
      e.name === 'NotAllowedError'
        ? '摄像头权限被拒绝，请在浏览器地址栏允许摄像头访问'
        : e.message || '无法打开摄像头'
    camActive.value = false
  }
}

function stopCam() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
    stream = null
  }
  camActive.value = false
}

function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas || video.videoWidth === 0) return
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  capturedImg.value = canvas.toDataURL('image/jpeg', 0.92)
  file.value = null
  stopCam()
}

function resetCapture() {
  capturedImg.value = ''
  camError.value = ''
  stopCam()
}

function dataURLtoBlob(dataUrl) {
  const [head, b64] = dataUrl.split(',')
  const mime = (head.match(/:(.*?);/) || [])[1] || 'image/jpeg'
  const bin = atob(b64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new Blob([arr], { type: mime })
}

async function submit() {
  if (!name.value.trim()) {
    msg.value = '请输入姓名'
    msgType.value = 'warn'
    return
  }
  let blob = null
  if (capturedImg.value) blob = dataURLtoBlob(capturedImg.value)
  else if (file.value) blob = file.value
  if (!blob) {
    msg.value = '请先拍照或选择照片'
    msgType.value = 'warn'
    return
  }
  busy.value = true
  msg.value = ''
  try {
    const fd = new FormData()
    fd.append('name', name.value.trim())
    fd.append('file', blob, 'capture.jpg')
    await api.upload('/api/faces/register', fd)
    msg.value = '注册成功'
    msgType.value = 'ok'
    name.value = ''
    capturedImg.value = ''
    file.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    await loadFaces()
  } catch (err) {
    msg.value = FACE_ERRORS[err.message] || err.message || '注册失败'
    msgType.value = 'danger'
  } finally {
    busy.value = false
  }
}

async function removeFace(id) {
  if (!confirm('确认删除该人脸？')) return
  try {
    await api.del('/api/faces/' + id)
    await loadFaces()
  } catch (err) {
    msg.value = err.message || '删除失败'
    msgType.value = 'danger'
  }
}

onBeforeUnmount(stopCam)
onMounted(loadFaces)
</script>

<template>
  <div class="face-page">
    <div class="panel form-panel">
      <div class="panel-title">
        <span>注册人脸</span>
        <span class="hint">ENROLL</span>
      </div>
      <div class="panel-body form-body">
        <label class="field">
          <span class="field-label">姓名</span>
          <input v-model="name" class="input mono" placeholder="例如：张三" maxlength="128" />
        </label>

        <div class="field">
          <span class="field-label">拍照采集</span>
          <div class="cam-box">
            <img v-if="capturedImg" :src="capturedImg" alt="已采集照片" class="cam-shot" />
            <video
              v-else-if="camActive"
              ref="videoRef"
              class="cam-video"
              autoplay
              playsinline
              muted
            ></video>
            <div v-else class="cam-placeholder">CAMERA OFF</div>
            <canvas ref="canvasRef" hidden></canvas>
          </div>
          <p v-if="camError" class="form-msg warn">{{ camError }}</p>
          <div class="cam-actions">
            <button
              v-if="!camActive && !capturedImg"
              class="btn primary"
              type="button"
              @click="startCam"
            >
              打开摄像头
            </button>
            <button v-else-if="camActive" class="btn primary" type="button" @click="capture">
              拍照
            </button>
            <button v-if="capturedImg" class="btn ghost" type="button" @click="resetCapture">
              重拍
            </button>
            <button v-if="camActive" class="btn ghost" type="button" @click="stopCam">关闭</button>
          </div>
        </div>

        <label class="field">
          <span class="field-label">或上传照片</span>
          <input
            ref="fileInputRef"
            id="face-file"
            type="file"
            accept="image/*"
            class="input"
            @change="onFile"
          />
        </label>

        <div class="form-actions">
          <button class="btn primary" :disabled="busy" @click="submit">
            {{ busy ? '处理中...' : '注册' }}
          </button>
        </div>
        <p v-if="msg" class="form-msg" :class="msgType">{{ msg }}</p>
      </div>
    </div>

    <div class="panel list-panel">
      <div class="panel-title">
        <span>已注册人脸</span>
        <span class="hint">{{ faces.length }} 人</span>
      </div>
      <div class="panel-body">
        <div v-if="faces.length === 0" class="stub">NO REGISTERED FACES</div>
        <ul v-else class="face-list">
          <li v-for="f in faces" :key="f.id" class="face-item">
            <img v-if="f.thumbnail" :src="f.thumbnail" alt="" class="face-thumb" />
            <span v-else class="face-thumb placeholder"></span>
            <div class="face-meta">
              <span class="face-name">{{ f.person_name }}</span>
              <span class="face-time mono">{{ f.created_at }}</span>
            </div>
            <button class="btn ghost" @click="removeFace(f.id)">删除</button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.face-page {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: var(--gap);
  height: 100%;
  min-height: 0;
  padding-top: var(--gap);
}

.form-panel {
  min-height: 0;
}

.list-panel {
  min-height: 0;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
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

/* 摄像头采集区 */
.cam-box {
  width: 100%;
  aspect-ratio: 4 / 3;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cam-video,
.cam-shot {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cam-placeholder {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.15em;
  color: var(--text-dim);
}

.cam-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.form-actions {
  margin-top: 4px;
}

.btn {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 8px 16px;
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

.btn.ghost:hover {
  background: rgba(242, 95, 92, 0.1);
  border-color: rgba(242, 95, 92, 0.4);
  color: var(--danger);
}

.form-msg {
  font-size: 13px;
  margin: 0;
}

.form-msg.ok {
  color: var(--ok);
}

.form-msg.warn {
  color: var(--warn);
}

.form-msg.danger {
  color: var(--danger);
}

.face-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.face-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
}

.face-thumb {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  object-fit: cover;
  flex: 0 0 auto;
}

.face-thumb.placeholder {
  background: rgba(255, 255, 255, 0.06);
}

.face-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.face-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.face-time {
  font-size: 11px;
  color: var(--text-dim);
}

@media (max-width: 899px) {
  .face-page {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}
</style>
