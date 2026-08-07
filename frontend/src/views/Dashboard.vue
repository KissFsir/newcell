<script setup>
import EmotionBadge from '../components/EmotionBadge.vue'
import ExpressionPanel from '../components/ExpressionPanel.vue'
import VideoStream from '../components/VideoStream.vue'
import IdentityPanel from '../components/IdentityPanel.vue'
import PhysioChart from '../components/PhysioChart.vue'
</script>

<template>
  <div class="dashboard">
    <EmotionBadge />
    <ExpressionPanel />
    <VideoStream />
    <IdentityPanel />
    <PhysioChart />
  </div>
</template>
