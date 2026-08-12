<script setup>
import StatusBar from './components/StatusBar.vue'
import ReportPromptModal from './components/ReportPromptModal.vue'
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark"></span>
        <span class="brand-name mono">NEWCELL</span>
        <span class="brand-sub">多模态情绪监控</span>
      </div>
      <nav class="nav">
        <RouterLink to="/" class="nav-link">监控面板</RouterLink>
        <RouterLink to="/faces" class="nav-link">人脸注册</RouterLink>
        <RouterLink to="/reports" class="nav-link">报告</RouterLink>
        <RouterLink to="/settings" class="nav-link">设置</RouterLink>
      </nav>
    </header>

    <main class="main">
      <RouterView />
    </main>

    <StatusBar />
    <ReportPromptModal />
  </div>
</template>
