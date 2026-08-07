import { computed } from 'vue'
import { createSharedComposable, useEventSource } from '@vueuse/core'

/**
 * 共享单条 SSE 连接：所有面板复用同一 EventSource。
 * 后端 /api/stream 每 3s 推送 data: {snapshot json}
 */
function useSnapshotStreamRaw() {
  const { status, data, eventSource, error } = useEventSource('/api/stream', undefined, {
    autoReconnect: {
      retries: Infinity,
      delay: 3000,
    },
  })

  const snapshot = computed(() => {
    if (!data.value) return null
    try {
      return JSON.parse(data.value)
    } catch {
      return null
    }
  })

  return { status, snapshot, eventSource, error }
}

export const useSnapshotStream = createSharedComposable(useSnapshotStreamRaw)
