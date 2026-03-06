 <script setup lang="ts">
  defineProps<{
    accessKey: {
      id: string
      ss_port: number
      ss_method: string
      ss_url: string | null
      qr_code: string | null
      traffic_up: number
      traffic_down: number
      is_active: boolean
      server_name: string | null
      server_country: string | null
    }
  }>()

  const emit = defineEmits<{
    delete: [id: string]
    regenerate: [id: string]
  }>()

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }
  </script>

  <template>
    <div class="key-card">
      <div class="key-header">
        <div>
          <strong>{{ accessKey.server_name }}</strong>
          <span class="country">{{ accessKey.server_country }}</span>
        </div>
        <span class="port">:{{ accessKey.ss_port }}</span>
      </div>

      <div class="key-details">
        <div class="detail-row">
          <span class="label">Method</span>
          <span>{{ accessKey.ss_method }}</span>
        </div>
        <div class="detail-row">
          <span class="label">Traffic</span>
          <span>↑ {{ formatBytes(accessKey.traffic_up) }} / ↓ {{ formatBytes(accessKey.traffic_down) }}</span>
        </div>
      </div>

      <div v-if="accessKey.ss_url" class="ss-url">
        <code>{{ accessKey.ss_url }}</code>
        <button class="btn-copy" @click="copyToClipboard(accessKey.ss_url!)">Copy</button>
      </div>

      <div class="key-actions">
        <button class="btn-regen" @click="emit('regenerate', accessKey.id)">Regenerate</button>
        <button class="btn-delete" @click="emit('delete', accessKey.id)">Delete</button>
      </div>
    </div>
  </template>

  <style scoped>
  .key-card {
    padding: 16px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  }

  .key-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .country {
    margin-left: 8px;
    font-size: 13px;
    color: #888;
  }

  .port {
    font-family: monospace;
    font-size: 14px;
    color: #4a90d9;
  }

  .key-details {
    margin-bottom: 12px;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 4px 0;
  }

  .detail-row .label {
    color: #888;
  }

  .ss-url {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    background: #f5f5f5;
    border-radius: 4px;
    margin-bottom: 12px;
  }

  .ss-url code {
    flex: 1;
    font-size: 12px;
    word-break: break-all;
  }

  .btn-copy {
    padding: 4px 10px;
    border: 1px solid #4a90d9;
    background: transparent;
    color: #4a90d9;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .key-actions {
    display: flex;
    gap: 8px;
  }

  .btn-regen, .btn-delete {
    flex: 1;
    padding: 6px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-regen {
    background: #f0f0f0;
    color: #333;
  }

  .btn-delete {
    background: #fdecea;
    color: #c0392b;
  }

  .btn-regen:hover { background: #e0e0e0; }
  .btn-delete:hover { background: #f5c6cb; }
  </style>