
  <script setup lang="ts">
  import { computed } from 'vue'
  import { useAuthStore } from '@/stores/auth'

  interface UserProfile {
    email: string
    plan: string
    traffic_used: number
    traffic_limit: number
    is_active: boolean
  }

  const authStore = useAuthStore()

  const user = computed(() => authStore.user as UserProfile | null)

  function formatBytes(bytes: number): string {
    const gb = bytes / (1024 * 1024 * 1024)
    return gb.toFixed(2) + ' GB'
  }

  const trafficPercent = computed(() => {
    if (!user.value) return 0
    return Math.min((user.value.traffic_used / user.value.traffic_limit) * 100, 100)
  })
  </script>

  <template>
    <div class="profile-card" v-if="user">
      <div class="profile-header">
        <h2>{{ user.email }}</h2>
        <span class="plan-badge">{{ user.plan }}</span>
      </div>

      <div class="traffic-section">
        <div class="traffic-label">
          <span>Traffic</span>
          <span>{{ formatBytes(user.traffic_used) }} / {{ formatBytes(user.traffic_limit) }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: trafficPercent + '%' }" />
        </div>
      </div>

      <div class="profile-footer">
        <span class="status" :class="{ active: user.is_active }">
          {{ user.is_active ? 'Active' : 'Inactive' }}
        </span>
        <button class="btn-logout" @click="authStore.logout()">Logout</button>
      </div>
    </div>
  </template>

  <style scoped>
  .profile-card {
    padding: 24px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .profile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .profile-header h2 {
    margin: 0;
    font-size: 18px;
  }

  .plan-badge {
    padding: 4px 12px;
    background: #4a90d9;
    color: #fff;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .traffic-section {
    margin-bottom: 16px;
  }

  .traffic-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #666;
    margin-bottom: 6px;
  }

  .progress-bar {
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: #4a90d9;
    border-radius: 4px;
    transition: width 0.3s;
  }

  .profile-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .status {
    font-size: 13px;
    color: #999;
  }

  .status.active {
    color: #27ae60;
  }

  .btn-logout {
    padding: 6px 16px;
    border: 1px solid #e74c3c;
    background: transparent;
    color: #e74c3c;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-logout:hover {
    background: #e74c3c;
    color: #fff;
  }
  </style>
