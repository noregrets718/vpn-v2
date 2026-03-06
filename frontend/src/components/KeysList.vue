 <script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import api from '@/api/client'
  import KeyCard from '@/components/KeyCard.vue'
  import ServerSelect from '@/components/ServerSelect.vue'



  interface AccessKey {
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

  const keys = ref<AccessKey[]>([])
  const loading = ref(false)
  const creating = ref(false)
  const showServerSelect = ref(false)
  const error = ref('')

  const emit = defineEmits<{
    keysLoaded: [keys: AccessKey[]]
  }>()

  async function loadKeys() {
    loading.value = true
    try {
      keys.value = await api.get('/keys/my')
      emit('keysLoaded', keys.value)
    } catch {
      keys.value = []
    } finally {
      loading.value = false
    }
  }

  async function createKey(serverId: string) {
    creating.value = true
    error.value = ''
    try {
      await api.post('/keys/create', { server_id: serverId })
      showServerSelect.value = false
      await loadKeys()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to create key'
    } finally {
      creating.value = false
    }
  }

  async function deleteKey(keyId: string) {
    try {
      await api.del(`/keys/${keyId}`)
      await loadKeys()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to delete key'
    }
  }

  async function regenerateKey(keyId: string) {
    try {
      await api.post(`/keys/${keyId}/regenerate`)
      await loadKeys()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to regenerate key'
    }
  }

  onMounted(loadKeys)
  </script>

  <template>
    <div class="keys-list">
      <div class="keys-header">
        <h3>VPN Keys</h3>
        <button class="btn-create" @click="showServerSelect = !showServerSelect" :disabled="creating">
          {{ showServerSelect ? 'Cancel' : '+ New Key' }}
        </button>
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <div v-if="showServerSelect" class="create-section">
        <p>Select a server:</p>
        <ServerSelect @select="createKey" />
        <p v-if="creating" class="creating-msg">Creating key...</p>
      </div>

      <div v-if="loading" class="loading">Loading keys...</div>

      <div v-else-if="keys.length === 0" class="empty">
        No VPN keys yet. Create one to get started.
      </div>

      <div v-else class="keys-grid">
        <KeyCard
          v-for="key in keys"
          :key="key.id"
          :access-key="key"
          @delete="deleteKey"
          @regenerate="regenerateKey"
        />
      </div>
    </div>
  </template>

  <style scoped>
  .keys-list {
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .keys-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .keys-header h3 {
    margin: 0;
  }

  .btn-create {
    padding: 8px 16px;
    background: #4a90d9;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-create:hover:not(:disabled) { opacity: 0.85; }
  .btn-create:disabled { opacity: 0.5; cursor: not-allowed; }

  .create-section {
    padding: 16px;
    background: #f9f9f9;
    border-radius: 4px;
    margin-bottom: 16px;
  }

  .create-section p {
    margin: 0 0 8px;
    font-size: 14px;
  }

  .creating-msg {
    color: #4a90d9;
    font-style: italic;
  }

  .error-msg {
    padding: 8px 12px;
    background: #fdecea;
    color: #c0392b;
    border-radius: 4px;
    font-size: 13px;
    margin-bottom: 12px;
  }

  .loading, .empty {
    text-align: center;
    color: #888;
    padding: 24px;
    font-size: 14px;
  }

  .keys-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  </style>
