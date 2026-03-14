<script setup lang="ts">                                                                                                                           
  import { ref } from 'vue'                                                                                                                        
  import ServersAdmin from '@/components/ServersAdmin.vue'
  import UsersAdmin from '@/components/UsersAdmin.vue'

  const activeTab = ref<'servers' | 'users'>('servers')
  </script>

  <template>
    <div class="admin-view">
      <div class="admin-header">
        <RouterLink to="/" class="back-link">← Dashboard</RouterLink>
        <h1>Панель администратора</h1>
      </div>

      <div class="tabs">
        <button :class="{ active: activeTab === 'servers' }" @click="activeTab = 'servers'">
          Серверы
        </button>
        <button :class="{ active: activeTab === 'users' }" @click="activeTab = 'users'">
          Пользователи
        </button>
      </div>

      <ServersAdmin v-if="activeTab === 'servers'" />
      <UsersAdmin v-if="activeTab === 'users'" />
    </div>
  </template>

  <style scoped>
  .admin-view {
    max-width: 1000px;
    margin: 0 auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    background: #f5f5f5;
    min-height: 100vh;
  }
  .admin-header {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .admin-header h1 {
    margin: 0;
    font-size: 22px;
  }
  .back-link {
    color: #4a90d9;
    text-decoration: none;
    font-size: 14px;
  }
  .tabs {
    display: flex;
    gap: 4px;
    background: #fff;
    padding: 4px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,.1);
    width: fit-content;
  }
  .tabs button {
    padding: 8px 24px;
    border: none;
    background: transparent;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    color: #666;
  }
  .tabs button.active {
    background: #4a90d9;
    color: #fff;
  }
  </style>
