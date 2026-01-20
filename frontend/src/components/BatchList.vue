<template>
  <div class="batch-list">
    <div class="batch-header">
      <h4>批次详情</h4>
      <span class="batch-summary">
        成功: {{ succeededCount }} / 失败: {{ failedCount }} / 总计: {{ batches.length }}
      </span>
    </div>

    <el-table :data="batches" size="small" max-height="300">
      <el-table-column prop="index" label="批次" width="70" align="center">
        <template #default="{ row }">
          #{{ row.index + 1 }}
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="尝试次数" width="90" align="center">
        <template #default="{ row }">
          {{ row.attempts }} / {{ row.max_attempts }}
        </template>
      </el-table-column>

      <el-table-column label="详情" min-width="150">
        <template #default="{ row }">
          <span v-if="row.error" class="error-text">{{ row.error }}</span>
          <span v-else-if="row.status === 'succeeded'" class="success-text">完成</span>
          <span v-else-if="row.status === 'running'" class="running-text">处理中...</span>
          <span v-else class="pending-text">等待中</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="80" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            type="primary"
            link
            size="small"
            :loading="retryingIdx === row.index"
            @click="handleRetry(row.index)"
          >
            重试
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="batch-actions" v-if="showAggregate">
      <el-button type="warning" @click="$emit('aggregate')">
        手动汇总成功批次
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Batch } from '@/types'

const props = defineProps<{
  batches: Batch[]
  showAggregate?: boolean
}>()

const emit = defineEmits<{
  retry: [batchIdx: number]
  aggregate: []
}>()

const retryingIdx = ref<number | null>(null)

const succeededCount = computed(() =>
  props.batches.filter(b => b.status === 'succeeded').length
)

const failedCount = computed(() =>
  props.batches.filter(b => b.status === 'failed').length
)

function getStatusType(status: string) {
  switch (status) {
    case 'succeeded': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'primary'
    default: return 'info'
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'succeeded': return '成功'
    case 'failed': return '失败'
    case 'running': return '运行中'
    case 'pending': return '等待'
    default: return status
  }
}

async function handleRetry(batchIdx: number) {
  retryingIdx.value = batchIdx
  emit('retry', batchIdx)
  setTimeout(() => {
    retryingIdx.value = null
  }, 2000)
}
</script>

<style scoped>
.batch-list {
  margin-top: 20px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.batch-header h4 {
  margin: 0;
  font-size: 14px;
  color: #303133;
}

.batch-summary {
  font-size: 12px;
  color: #909399;
}

.error-text {
  color: #f56c6c;
  font-size: 12px;
}

.success-text {
  color: #67c23a;
  font-size: 12px;
}

.running-text {
  color: #409eff;
  font-size: 12px;
}

.pending-text {
  color: #909399;
  font-size: 12px;
}

.batch-actions {
  margin-top: 16px;
  text-align: center;
}
</style>
