<script setup lang="ts">                                                                                                                           
  import { ref, onMounted } from 'vue'                  
  import api from '@/api/client'

  interface AdminUser {
    id: string
    email: string
    plan: 'free' | 'basic' | 'pro'
    traffic_used: number
    traffic_limit: number
    is_active: boolean
    is_admin: boolean
    created_at: string
    active_key_count: number
  }

  const users = ref<AdminUser[]>([])
  const editingId = ref<string | null>(null)
  const editForm = ref({ plan: 'free' as AdminUser['plan'], traffic_limit_gb: 5, is_active: true })

  function toGb(bytes: number) {
    return (bytes / 1_073_741_824).toFixed(2)
  }

  function fromGb(gb: number) {
    return Math.round(gb * 1_073_741_824)
  }

  async function loadUsers() {
    try {
      users.value = await api.get('/admin/users')
    } catch {
      users.value = []
    }
  }

  function startEdit(user: AdminUser) {
    editingId.value = user.id
    editForm.value = {
      plan: user.plan,
      traffic_limit_gb: parseFloat(toGb(user.traffic_limit)),
      is_active: user.is_active,
    }
  }

  function cancelEdit() {
    editingId.value = null
  }

  async function saveEdit(userId: string) {
    const updated = await api.patch(`/admin/users/${userId}`, {
      plan: editForm.value.plan,
      traffic_limit: fromGb(editForm.value.traffic_limit_gb),
      is_active: editForm.value.is_active,
    })
    const idx = users.value.findIndex(u => u.id === userId)
    if (idx !== -1) users.value[idx] = updated
    editingId.value = null
  }

  onMounted(loadUsers)
  </script>

  <template>
    <div class="users-admin">
      <div class="header">
        <h2>Пользователи</h2>
        <span class="count">{{ users.length }} всего</span>
      </div>

      <table v-if="users.length > 0">
        <thead>
          <tr>
            <th>Email</th>
            <th>План</th>
            <th>Трафик</th>
            <th>Лимит</th>
            <th>Ключей</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.email }}<span v-if="user.is_admin" class="admin-badge">admin</span></td>

            <td>
              <select v-if="editingId === user.id" v-model="editForm.plan">
                <option value="free">free</option>
                <option value="basic">basic</option>
                <option value="pro">pro</option>
              </select>
              <span v-else class="plan-badge" :class="user.plan">{{ user.plan }}</span>
            </td>

            <td>{{ toGb(user.traffic_used) }} GB</td>

            <td>
              <span v-if="editingId === user.id">
                <input type="number" v-model.number="editForm.traffic_limit_gb" min="1" step="1" style="width:70px" /> GB
              </span>
              <span v-else>{{ toGb(user.traffic_limit) }} GB</span>
            </td>

            <td>{{ user.active_key_count }}</td>

            <td>
              <label v-if="editingId === user.id">
                <input type="checkbox" v-model="editForm.is_active" /> активен
              </label>
              <span v-else :class="user.is_active ? 'active' : 'inactive'">
                {{ user.is_active ? '● активен' : '● отключён' }}
              </span>
            </td>

            <td class="actions">
              <template v-if="editingId === user.id">
                <button class="btn-primary" @click="saveEdit(user.id)">Сохранить</button>
                <button @click="cancelEdit">Отмена</button>
              </template>
              <button v-else @click="startEdit(user)">Изменить</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">Пользователей нет</p>
    </div>
  </template>

  <style scoped>
  .users-admin { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.1); }
  .header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
  h2 { margin: 0; font-size: 18px; }
  .count { color: #888; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }
  th { color: #888; font-weight: 500; }
  .actions { display: flex; gap: 6px; }
  .btn-primary { background: #4a90d9; color: #fff; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; }
  button { padding: 4px 10px; border: 1px solid #ddd; background: #fff; border-radius: 4px; cursor: pointer; }
  .plan-badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 500; }
  .plan-badge.free { background: #f0f0f0; color: #666; }
  .plan-badge.basic { background: #e8f4fd; color: #2980b9; }
  .plan-badge.pro { background: #fef9e7; color: #f39c12; }
  .admin-badge { margin-left: 6px; padding: 1px 6px; background: #e74c3c; color: #fff; border-radius: 10px; font-size: 11px; }
  .active { color: #27ae60; font-weight: 500; }
  .inactive { color: #e74c3c; font-weight: 500; }
  .empty { color: #888; text-align: center; padding: 20px 0; }
  </style>
