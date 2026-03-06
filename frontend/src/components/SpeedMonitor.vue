 <script setup lang="ts">                                                                                                                                                  
  import { ref, watch, onUnmounted } from 'vue'

  const props = defineProps<{
    keyId: string | null
  }>()

  interface SpeedData {
    upload_speed_mbps: number
    download_speed_mbps: number
    upload_total_gb: number
    download_total_gb: number
  }

  const speed = ref<SpeedData | null>(null)
  const connected = ref(false)
  let ws: WebSocket | null = null

  function connect(keyId: string) {
    disconnect()

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/speed/${keyId}`)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      try {
        speed.value = JSON.parse(event.data)
      } catch {
        // ignore
      }
    }

    ws.onclose = () => {
      connected.value = false
      // reconnect after 3s
      setTimeout(() => {
        if (props.keyId === keyId) {
          connect(keyId)
        }
      }, 3000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
    speed.value = null
  }

  watch(() => props.keyId, (newId) => {
    if (newId) {
      connect(newId)
    } else {
      disconnect()
    }
  }, { immediate: true })

  onUnmounted(disconnect)
  </script>

  <template>
    <div class="speed-monitor" v-if="keyId">
      <h3>
        Real-time Speed
        <span class="status-dot" :class="{ connected }" />
      </h3>

      <div v-if="speed" class="speed-grid">
        <div class="speed-card upload">
          <span class="direction">↑ Upload</span>
          <span class="value">{{ speed.upload_speed_mbps.toFixed(2) }} Mbps</span>
          <span class="total">Total: {{ speed.upload_total_gb.toFixed(3) }} GB</span>
        </div>
        <div class="speed-card download">
          <span class="direction">↓ Download</span>
          <span class="value">{{ speed.download_speed_mbps.toFixed(2) }} Mbps</span>
          <span class="total">Total: {{ speed.download_total_gb.toFixed(3) }} GB</span>
        </div>
      </div>

      <div v-else class="waiting">
        {{ connected ? 'Waiting for data...' : 'Connecting...' }}
      </div>
    </div>
  </template>

  <style scoped>
  .speed-monitor {
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .speed-monitor h3 {
    margin: 0 0 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ccc;
  }

  .status-dot.connected {
    background: #27ae60;
  }

  .speed-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .speed-card {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 16px;
    border-radius: 6px;
  }

  .speed-card.upload {
    background: #eef6ff;
  }

  .speed-card.download {
    background: #eefff3;
  }

  .direction {
    font-size: 12px;
    color: #888;
    font-weight: 600;
  }

  .value {
    font-size: 24px;
    font-weight: 700;
  }

  .upload .value { color: #4a90d9; }
  .download .value { color: #27ae60; }

  .total {
    font-size: 12px;
    color: #888;
  }

  .waiting {
    text-align: center;
    color: #888;
    padding: 24px;
  }
  </style>
