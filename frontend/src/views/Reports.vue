<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import ReportView from '../components/ReportView.vue'

const reports = ref([])
const persons = ref([])
const err = ref('')
const active = ref(null)
const filterPerson = ref('')
const filterStart = ref('')
const filterEnd = ref('')

async function load() {
  try {
    const params = new URLSearchParams()
    if (filterPerson.value) params.set('person', filterPerson.value)
    if (filterStart.value) params.set('start', new Date(filterStart.value + 'T00:00:00').toISOString())
    if (filterEnd.value) params.set('end', new Date(filterEnd.value + 'T23:59:59').toISOString())
    const q = params.toString()
    const d = await api.get('/api/reports' + (q ? '?' + q : ''))
    reports.value = d.reports || []
    persons.value = d.persons || []
  } catch (e) {
    err.value = e.message || '加载失败'
  }
}

function resetFilter() {
  filterPerson.value = ''
  filterStart.value = ''
  filterEnd.value = ''
  load()
}

function openReport(r) {
  active.value = r
}

async function removeReport(r) {
  if (!confirm(`确认删除报告「${r.person_name} · ${new Date(r.created_at).toLocaleString('zh-CN', { hour12: false })}」？`)) return
  try {
    await api.del('/api/reports/' + r.id)
    await load()
  } catch (e) {
    err.value = e.message || '删除失败'
  }
}

onMounted(load)
</script>

<template>
  <div class="panel reports-panel">
    <div class="panel-title">
      <span>报告历史</span>
      <span class="hint">REPORTS</span>
    </div>
    <div class="panel-body">
      <div class="filter-bar">
        <select v-model="filterPerson" class="input mono" @change="load">
          <option value="">全部人员</option>
          <option v-for="p in persons" :key="p" :value="p">{{ p }}</option>
        </select>
        <input v-model="filterStart" type="date" class="input mono" @change="load" />
        <span class="sep mono">~</span>
        <input v-model="filterEnd" type="date" class="input mono" @change="load" />
        <button class="btn ghost" @click="resetFilter">清除</button>
        <span class="count mono">共 {{ reports.length }} 份</span>
      </div>

      <p v-if="err" class="reports-err mono">{{ err }}</p>
      <div v-if="!reports.length && !err" class="stub">NO REPORTS</div>
      <ul v-else class="report-list">
        <li v-for="r in reports" :key="r.id" class="report-item">
          <div class="report-meta">
            <span class="report-name">{{ r.person_name }}</span>
            <span class="report-mode mono">{{ r.mode === 'ai' ? 'AI 全文' : '结构化' }}</span>
            <span class="report-time mono">
              {{ new Date(r.created_at).toLocaleString('zh-CN', { hour12: false }) }}
            </span>
          </div>
          <button class="btn ghost" @click="openReport(r)">查看</button>
          <button class="btn ghost danger" @click="removeReport(r)">删除</button>
        </li>
      </ul>
    </div>
  </div>

  <ReportView v-if="active" :report="active" @close="active = null" />
</template>

<style scoped>
.reports-panel {
  max-width: 860px;
  margin: var(--gap) auto 0;
  min-height: 0;
}

.reports-err {
  margin: 0;
  font-size: 12px;
  color: var(--warn);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--panel-border);
}

.input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  color: var(--text);
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
}

.input:focus {
  border-color: var(--accent);
}

.sep {
  color: var(--text-dim);
  font-size: 12px;
}

.count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-dim);
}

.report-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
}

.report-meta {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
  flex: 1 1 auto;
}

.report-name {
  font-size: 14px;
  font-weight: 600;
}

.report-mode {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--panel-border);
  color: var(--accent);
  flex: 0 0 auto;
}

.report-time {
  font-size: 12px;
  color: var(--text-dim);
}

.btn.ghost {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 6px 14px;
  background: transparent;
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  flex: 0 0 auto;
}

.btn.ghost:hover {
  color: var(--accent);
  border-color: rgba(34, 211, 198, 0.4);
}

.btn.ghost.danger:hover {
  color: var(--danger);
  border-color: rgba(242, 95, 92, 0.4);
}
</style>
