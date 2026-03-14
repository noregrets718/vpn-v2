<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import api from '@/api/client'

  interface Server {
    id: string
    name: string
    ip_address: string
    country: string
    city: string | null
    is_active: boolean
    current_load: number
    connected_users: number
    active_instances: number
    is_local?: boolean
  }

  const servers = ref<Server[]>([])
  const showForm = ref(false)
  const healthStatus = ref<Record<string, { online: boolean; active_instances: number }>>({})

  const form = ref({
    name: '',
    ip_address: '',
    country: '',
    city: '',
    is_local: true,
    agent_url: '',
    agent_token: '',
  })

  async function loadServers() {
    try {
      servers.value = await api.get('/admin/servers')
    } catch {
      servers.value = []
    }
  }

  async function createServer() {
    const payload: Record<string, unknown> = {
      name: form.value.name,
      country: form.value.country,
      city: form.value.city || null,
      is_local: form.value.is_local,
    }
    if (!form.value.is_local) {
      payload.agent_url = form.value.agent_url
      payload.agent_token = form.value.agent_token
    }
    await api.post('/servers', payload)
    showForm.value = false
    form.value = { name: '', ip_address: '', country: '', city: '', is_local: true, agent_url: '', agent_token: '' }
    await loadServers()
  }

  async function deleteServer(id: string) {
    await api.del(`/servers/${id}`)
    await loadServers()
  }

  async function checkHealth(id: string) {
    try {
      const data = await api.get(`/servers/${id}/health`)
      healthStatus.value[id] = data
    } catch {
      healthStatus.value[id] = { online: false, active_instances: 0 }
    }
  }

  onMounted(loadServers)
  </script>

  <template>
    <div class="servers-admin">
      <div class="header">
        <h2>Серверы</h2>
        <button class="btn-primary" @click="showForm = !showForm">+ Добавить сервер</button>
      </div>

      <div v-if="showForm" class="form-card">
        <h3>Новый сервер</h3>
        <div class="form-grid">
          <label>Имя*</label>
          <input v-model="form.name" placeholder="DE-Frankfurt-1" />

          <label>Страна*</label>
          <input v-model="form.country" placeholder="DE" />

          <label>Город</label>
          <input v-model="form.city" placeholder="Frankfurt" />

          <label>Локальный</label>
          <input type="checkbox" v-model="form.is_local" />

          <template v-if="!form.is_local">
            <label>Agent URL*</label>
            <input v-model="form.agent_url" placeholder="http://1.2.3.4:9000" />

            <label>Agent Token*</label>
            <input v-model="form.agent_token" type="password" placeholder="secret" />
          </template>
        </div>
        <div class="form-actions">
          <button class="btn-primary" @click="createServer">Создать</button>
          <button @click="showForm = false">Отмена</button>
        </div>
      </div>

      <table v-if="servers.length > 0">
        <thead>
          <tr>
            <th>Имя</th>
            <th>Страна / Город</th>
            <th>IP</th>
            <th>Тип</th>
            <th>Ключей</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in servers" :key="s.id">
            <td>{{ s.name }}</td>
            <td>{{ s.country }}{{ s.city ? ` / ${s.city}` : '' }}</td>
            <td>{{ s.ip_address }}</td>
            <td>{{ s.is_local ? 'local' : 'remote' }}</td>
            <td>{{ s.active_instances}}</td>
            <td>
              <span v-if="healthStatus[s.id]" :class="healthStatus[s.id].online ? 'online' : 'offline'">
                {{ healthStatus[s.id].online ? '● online' : '● offline' }}
              </span>
              <span v-else class="unknown">—</span>
            </td>
            <td class="actions">
              <button @click="checkHealth(s.id)">Проверить</button>
              <button class="btn-danger" @click="deleteServer(s.id)">Удалить</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">Серверов нет</p>
    </div>
  </template>

  <style scoped>
  .servers-admin { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.1); }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  h2 { margin: 0; font-size: 18px; }
  .form-card { background: #f9f9f9; border: 1px solid #eee; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
  .form-card h3 { margin: 0 0 12px; font-size: 15px; }
  .form-grid { display: grid; grid-template-columns: 120px 1fr; gap: 8px; align-items: center; }
  .form-grid input[type="text"], .form-grid input:not([type="checkbox"]) { padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; }
  .form-actions { display: flex; gap: 8px; margin-top: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }
  th { color: #888; font-weight: 500; }
  .actions { display: flex; gap: 6px; }
  .btn-primary { background: #4a90d9; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; }
  .btn-danger { background: #e74c3c; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
  button { padding: 4px 10px; border: 1px solid #ddd; background: #fff; border-radius: 4px; cursor: pointer; }
  .online { color: #27ae60; font-weight: 500; }
  .offline { color: #e74c3c; font-weight: 500; }
  .unknown { color: #aaa; }
  .empty { color: #888; text-align: center; padding: 20px 0; }
  </style>
