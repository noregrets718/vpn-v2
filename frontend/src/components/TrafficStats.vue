 <script setup lang="ts">                                                                                                                                                  
  import { ref, onMounted } from 'vue'
  import api from '@/api/client'

  interface TrafficSummary {
    traffic_used: number
    traffic_limit: number
    traffic_up: number
    traffic_down: number
    usage_percent: number
  }

  interface HistoryPoint {
    timestamp: string
    bytes_up: number
    bytes_down: number
    upload_speed: number
    download_speed: number
  }

  const props = defineProps<{
    keyIds: string[]
  }>()

  const summary = ref<TrafficSummary | null>(null)
  const history = ref<HistoryPoint[]>([])
  const selectedKeyId = ref<string>('')
  const selectedPeriod = ref<string>('24h')
  const loading = ref(false)

  const periods = ['1h', '24h', '7d', '30d']

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  function formatSpeed(mbps: number): string {
    return mbps.toFixed(2) + ' Mbps'
  }

  async function loadSummary() {
    try {
      summary.value = await api.get('/traffic/my')
    } catch {
      summary.value = null
    }
  }

  async function loadHistory() {
    if (!selectedKeyId.value) {
      history.value = []
      return
    }
    loading.value = true
    try {
      history.value = await api.get(`/traffic/key/${selectedKeyId.value}/history?period=${selectedPeriod.value}`)
    } catch {
      history.value = []
    } finally {
      loading.value = false
    }
  }

  function selectKey(keyId: string) {
    selectedKeyId.value = keyId
    loadHistory()
  }

  function selectPeriod(period: string) {
    selectedPeriod.value = period
    loadHistory()
  }

  onMounted(loadSummary)
  </script>

  <template>
    <div class="traffic-stats">
      <h3>Traffic</h3>

      <div v-if="summary" class="summary">
        <div class="stat-row">
          <span class="label">Total Used</span>
          <span>{{ formatBytes(summary.traffic_used) }} / {{ formatBytes(summary.traffic_limit) }}</span>
        </div>
        <div class="stat-row">
          <span class="label">Upload</span>
          <span>{{ formatBytes(summary.traffic_up) }}</span>
        </div>
        <div class="stat-row">
          <span class="label">Download</span>
          <span>{{ formatBytes(summary.traffic_down) }}</span>
        </div>
        <div class="stat-row">
          <span class="label">Usage</span>
          <span>{{ summary.usage_percent.toFixed(1) }}%</span>
        </div>
      </div>

      <div v-if="keyIds.length > 0" class="history-section">
        <h4>History by Key</h4>

        <div class="key-tabs">
          <button
            v-for="id in keyIds"
            :key="id"
            :class="{ active: selectedKeyId === id }"
            @click="selectKey(id)"
          >
            {{ id.slice(0, 8) }}...
          </button>
        </div>

        <div v-if="selectedKeyId" class="period-tabs">
          <button
            v-for="p in periods"
            :key="p"
            :class="{ active: selectedPeriod === p }"
            @click="selectPeriod(p)"
          >
            {{ p }}
          </button>
        </div>

        <div v-if="loading" class="loading">Loading...</div>

        <div v-else-if="history.length > 0" class="history-table">
          <div class="table-header">
            <span>Time</span>
            <span>Up</span>
            <span>Down</span>
            <span>Speed ↑</span>
            <span>Speed ↓</span>
          </div>
          <div v-for="(point, i) in history" :key="i" class="table-row">
            <span>{{ new Date(point.timestamp).toLocaleTimeString() }}</span>
            <span>{{ formatBytes(point.bytes_up) }}</span>
            <span>{{ formatBytes(point.bytes_down) }}</span>
            <span>{{ formatSpeed(point.upload_speed) }}</span>
            <span>{{ formatSpeed(point.download_speed) }}</span>
          </div>
        </div>

        <div v-else-if="selectedKeyId" class="empty">No history data for this period.</div>
      </div>
    </div>
  </template>

  <style scoped>
  .traffic-stats {
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .traffic-stats h3 {
    margin: 0 0 16px;
  }

  .traffic-stats h4 {
    margin: 16px 0 8px;
  }

  .summary {
    margin-bottom: 16px;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 14px;
    border-bottom: 1px solid #f0f0f0;
  }

  .stat-row .label {
    color: #888;
  }

  .key-tabs, .period-tabs {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .key-tabs button, .period-tabs button {
    padding: 4px 12px;
    border: 1px solid #ddd;
    background: #fff;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }

  .key-tabs button.active, .period-tabs button.active {
    background: #4a90d9;
    color: #fff;
    border-color: #4a90d9;
  }

  .table-header, .table-row {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr;
    gap: 8px;
    padding: 6px 0;
    font-size: 13px;
  }

  .table-header {
    font-weight: 600;
    border-bottom: 2px solid #e9ecef;
    color: #666;
  }

  .table-row {
    border-bottom: 1px solid #f0f0f0;
  }

  .loading, .empty {
    text-align: center;
    color: #888;
    padding: 16px;
    font-size: 14px;
  }
  </style>