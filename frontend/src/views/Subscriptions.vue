<template>
  <div class="subscriptions-page">
    <div class="page-header">
      <h2>定时订阅管理</h2>
      <p class="page-desc">配置每日自动运行的订阅，无需手动触发</p>
    </div>

    <!-- Create New Subscription -->
    <el-card class="create-card">
      <template #header>
        <span>创建新订阅</span>
      </template>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="CSV 文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".csv"
            :on-change="handleFileChange"
            :on-remove="() => (createForm.file = null)"
          >
            <template #trigger>
              <el-button type="primary">选择文件</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">请上传包含 Twitter 用户名的 CSV 文件</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="订阅名称">
          <el-input v-model="createForm.name" placeholder="可选，默认使用文件名" />
        </el-form-item>
        <el-form-item label="每日执行时间">
          <el-time-picker
            v-model="createForm.time"
            format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="createForm.enabled" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="subStore.loading" @click="handleCreate">
            创建订阅
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Subscription List -->
    <el-card class="list-card">
      <template #header>
        <div class="list-header">
          <span>已有订阅</span>
          <el-button size="small" @click="subStore.loadSubscriptions">刷新</el-button>
        </div>
      </template>
      
      <el-table :data="subStore.subscriptions" v-loading="subStore.loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            {{ row.name || row.csv_filename }}
          </template>
        </el-table-column>
        <el-table-column label="执行时间" width="100">
          <template #default="{ row }">
            {{ String(row.schedule_hour).padStart(2, '0') }}:{{ String(row.schedule_minute).padStart(2, '0') }}
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="80">
          <template #default="{ row }">
            {{ row.total_users ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上次运行" width="160">
          <template #default="{ row }">
            <template v-if="row.last_run">
              <div>{{ formatTime(row.last_run) }}</div>
              <el-tag :type="statusType(row.last_status)" size="small">
                {{ statusText(row.last_status) }}
              </el-tag>
            </template>
            <span v-else class="text-muted">未运行</span>
          </template>
        </el-table-column>
        <el-table-column label="下次运行" width="160">
          <template #default="{ row }">
            <span v-if="row.next_run && row.enabled">{{ formatTime(row.next_run) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button @click="handleRunNow(row.id)">立即运行</el-button>
              <el-button @click="handleToggle(row)">
                {{ row.enabled ? '禁用' : '启用' }}
              </el-button>
              <el-button type="danger" @click="handleDelete(row.id)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Error Message -->
    <el-alert v-if="subStore.error" type="error" :title="subStore.error" closable @close="subStore.error = null" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSubscriptionStore } from '@/stores/subscriptionStore'
import { useJobStore } from '@/stores/jobStore'
import { useRouter } from 'vue-router'
import type { Subscription } from '@/types'

const subStore = useSubscriptionStore()
const jobStore = useJobStore()
const router = useRouter()

const uploadRef = ref()
const createForm = reactive({
  file: null as File | null,
  name: '',
  time: new Date(2000, 0, 1, 8, 0),
  enabled: true,
})

onMounted(() => {
  subStore.loadSubscriptions()
})

function handleFileChange(file: any) {
  createForm.file = file.raw
}

async function handleCreate() {
  if (!createForm.file) {
    ElMessage.warning('请选择 CSV 文件')
    return
  }
  const hour = createForm.time.getHours()
  const minute = createForm.time.getMinutes()
  const id = await subStore.createSubscription(
    createForm.file,
    createForm.name || null,
    hour,
    minute,
    createForm.enabled
  )
  if (id) {
    ElMessage.success('订阅创建成功')
    createForm.file = null
    createForm.name = ''
    createForm.time = new Date(2000, 0, 1, 8, 0)
    uploadRef.value?.clearFiles()
  }
}

async function handleRunNow(subId: string) {
  const jobId = await subStore.runNow(subId)
  if (jobId) {
    ElMessage.success('任务已启动')
    jobStore.currentJobId = jobId
    router.push('/')
  }
}

async function handleToggle(sub: Subscription) {
  const success = await subStore.updateSubscription(sub.id, { enabled: !sub.enabled })
  if (success) {
    ElMessage.success(sub.enabled ? '已禁用' : '已启用')
  }
}

async function handleDelete(subId: string) {
  try {
    await ElMessageBox.confirm('确定要删除此订阅吗？', '确认删除', {
      type: 'warning',
    })
    const success = await subStore.deleteSubscription(subId)
    if (success) {
      ElMessage.success('删除成功')
    }
  } catch {
    // cancelled
  }
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusType(status: string | null): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'done':
      return 'success'
    case 'running':
    case 'summarizing':
    case 'queued':
      return 'warning'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}

function statusText(status: string | null): string {
  switch (status) {
    case 'done':
      return '完成'
    case 'running':
      return '运行中'
    case 'summarizing':
      return '生成摘要'
    case 'queued':
      return '排队中'
    case 'failed':
      return '失败'
    default:
      return '-'
  }
}
</script>

<style scoped>
.subscriptions-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.page-desc {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.create-card {
  margin-bottom: 0;
}

.list-card {
  margin-bottom: 0;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-muted {
  color: #909399;
}
</style>