<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'


interface ApiErrorData {
  message?: string
}

const router = useRouter()
const authStore = useAuthStore()

const email = ref<string>('')
const password = ref<string>('')
const error = ref<string>('')
const loading = ref<boolean>(false)

async function handleLogin(): Promise<void> {
  await submit(() => authStore.login(email.value, password.value))
}

async function handleRegister(): Promise<void> {
  await submit(() => authStore.register(email.value, password.value))
}

async function submit(action: () => Promise<void>): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await action()
    router.push('/')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrapper">
    <form class="login-form" @submit.prevent>
      <h2>Welcome</h2>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <label for="email">Email</label>
      <input
        id="email"
        v-model="email"
        type="email"
        placeholder="you@example.com"
        :disabled="loading"
        required
      />

      <label for="password">Password</label>
      <input
        id="password"
        v-model="password"
        type="password"
        placeholder="••••••••"
        :disabled="loading"
        required
      />

      <div class="btn-group">
        <button :disabled="loading" @click="handleLogin">
          {{ loading ? 'Please wait…' : 'Login' }}
        </button>
        <button :disabled="loading" class="btn-secondary" @click="handleRegister">
          Register
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f5f5;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 360px;
  padding: 32px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.login-form h2 {
  margin: 0 0 8px;
  text-align: center;
}

.login-form label {
  font-size: 14px;
  font-weight: 500;
}

.login-form input {
  padding: 10px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.login-form input:focus {
  border-color: #4a90d9;
}

.btn-group {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.btn-group button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  background: #4a90d9;
  color: #fff;
  transition: opacity 0.2s;
}

.btn-group button:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-group button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d !important;
}

.error-msg {
  padding: 8px 12px;
  background: #fdecea;
  color: #c0392b;
  border-radius: 4px;
  font-size: 13px;
}
</style>