<template>
  <div class="progress-panel">
    <div class="progress-header">
      <el-icon class="spinning"><Loading /></el-icon>
      <h3>{{ text }}</h3>
    </div>

    <el-progress
      :percentage="percent"
      :stroke-width="12"
      :show-text="true"
      status="primary"
    />

    <div class="progress-details" v-if="job">
      <span>任务 ID: {{ job.job_id.slice(0, 8) }}...</span>
      <span>批次大小: {{ job.batch_size }}</span>
      <span v-if="job.total_users">用户数: {{ job.total_users }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
import type { Job } from '@/types'

defineProps<{
  percent: number
  text: string
  job: Job | null
}>()
</script>

<style scoped>
.progress-panel {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.progress-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.spinning {
  font-size: 24px;
  color: #1da1f2;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.progress-details {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  font-size: 13px;
  color: #909399;
}
</style>
