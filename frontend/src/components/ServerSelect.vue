 <script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import api from '@/api/client'

  interface Server {
    id: string
    name: string
    country: string
    city: string | null
    is_active: boolean
  }

  const servers = ref<Server[]>([])
  const selected = ref<string>('')
  const loading = ref(false)

  const emit = defineEmits<{
    select: [serverId: string]
  }>()

  onMounted(async () => {
    loading.value = true
    try {
      servers.value = await api.get('/servers')
    } catch {
      servers.value = []
    } finally {
      loading.value = false
    }
  })

  function onSelect() {
    if (selected.value) {
      emit('select', selected.value)
    }
  }
  </script>

  <template>
    <div class="server-select">
      <select v-model="selected" :disabled="loading || servers.length === 0" @change="onSelect">
        <option value="" disabled>{{ loading ? 'Loading...' : 'Select server' }}</option>
        <option v-for="server in servers" :key="server.id" :value="server.id">
          {{ server.name }} — {{ server.country }}{{ server.city ? ', ' + server.city : '' }}
        </option>
      </select>
    </div>
  </template>

  <style scoped>
  .server-select select {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
    background: #fff;
    cursor: pointer;
  }

  .server-select select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  </style>
