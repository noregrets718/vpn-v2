 <script setup lang="ts">                                                                                                                                                  
  import { ref, onMounted } from 'vue'
  import api from '@/api/client'
  import ProfileCard from '@/components/ProfileCard.vue'
  import KeysList from '@/components/KeysList.vue'
  import TrafficStats from '@/components/TrafficStats.vue'
  import SpeedMonitor from '@/components/SpeedMonitor.vue'
  import { useAuthStore } from '@/stores/auth'
  import ServersAdmin from '@/components/ServersAdmin.vue'

  const authStore = useAuthStore()

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
  const selectedKeyId = ref<string | null>(null)

  async function loadKeys() {
    try {
      keys.value = await api.get('/keys/my')
    } catch {
      keys.value = []
    }
  }

  function onKeySelect(keyId: string) {
    selectedKeyId.value = selectedKeyId.value === keyId ? null : keyId
  }

  onMounted(loadKeys)
  </script>

  <template>
    <div class="dashboard">
      <ProfileCard />

      <KeysList @keys-updated="loadKeys" />

      <TrafficStats :key-ids="keys.map(k => k.id)" />

      <SpeedMonitor :key-id="selectedKeyId" />

      <div v-if="keys.length > 0" class="speed-select">
        <p>Select a key to monitor speed:</p>
        <div class="speed-buttons">
          <button
            v-for="key in keys"
            :key="key.id"
            :class="{ active: selectedKeyId === key.id }"
            @click="onKeySelect(key.id)"
          >
            {{ key.server_name }} :{{ key.ss_port }}
          </button>
        </div>
      </div>
        <ServersAdmin v-if="authStore.user?.is_admin" />
    </div>
  </template>

  <style scoped>
  .dashboard {
    max-width: 800px;
    margin: 0 auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    background: #f5f5f5;
    min-height: 100vh;
  }

  .speed-select {
    padding: 16px 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .speed-select p {
    margin: 0 0 8px;
    font-size: 14px;
    color: #666;
  }

  .speed-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .speed-buttons button {
    padding: 6px 14px;
    border: 1px solid #ddd;
    background: #fff;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }

  .speed-buttons button.active {
    background: #4a90d9;
    color: #fff;
    border-color: #4a90d9;
  }
  </style>
