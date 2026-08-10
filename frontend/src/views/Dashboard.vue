<script setup>
import VideoStream from '../components/VideoStream.vue'
import IdentityPanel from '../components/IdentityPanel.vue'
import VoiceActivityPanel from '../components/VoiceActivityPanel.vue'
import PhysioChart from '../components/PhysioChart.vue'
import TranscriptPanel from '../components/TranscriptPanel.vue'
import ResultPanel from '../components/ResultPanel.vue'
</script>

<template>
  <div class="dashboard">
    <VideoStream />
    <IdentityPanel />
    <VoiceActivityPanel />
    <PhysioChart />
    <TranscriptPanel />
    <ResultPanel />
  </div>
</template>
