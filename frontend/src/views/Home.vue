<template>
  <div class="home-page">
    <!-- 上传区域 -->
    <UploadZone
      v-if="!jobStore.currentJob"
      @file-selected="handleFileSelected"
    />

    <!-- 进度面板 -->
    <ProgressPanel
      v-else-if="jobStore.isProcessing"
      :percent="jobStore.progressPercent"
      :text="jobStore.progressText"
      :job="jobStore.currentJob"
      :show-aggregate="false"
      @retry-batch="jobStore.retryFailedBatch"
      @aggregate="jobStore.forceAggregate"
    />

    <!-- 结果展示 -->
    <template v-else-if="jobStore.isDone">
      <div class="result-actions">
        <el-button type="primary" @click="downloadCsv">
          <el-icon><Download /></el-icon>
          下载推文 CSV
        </el-button>
        <el-button @click="jobStore.reset">
          <el-icon><RefreshRight /></el-icon>
          重新开始
        </el-button>
      </div>
      <SummaryView :content="jobStore.summary" />
    </template>

    <!-- 错误状态 -->
    <div v-else-if="jobStore.isFailed" class="error-panel">
      <el-alert
        title="处理失败"
        type="error"
        :description="jobStore.error || '未知错误'"
        show-icon
      />

      <!-- 显示批次详情和汇总按钮 -->
      <ProgressPanel
        v-if="jobStore.currentJob?.batches && jobStore.currentJob.batches.length > 0"
        :percent="jobStore.progressPercent"
        :text="'部分批次失败'"
        :job="jobStore.currentJob"
        :show-aggregate="jobStore.canAggregate"
        @retry-batch="jobStore.retryFailedBatch"
        @aggregate="jobStore.forceAggregate"
      />

      <el-button style="margin-top: 16px" @click="jobStore.reset">
        重新开始
      </el-button>
    </div>

    <!-- 全局错误提示 -->
    <el-alert
      v-if="jobStore.error && !jobStore.isFailed"
      :title="jobStore.error"
      type="error"
      show-icon
      closable
      style="margin-top: 16px"
    />

    <!-- 历史记录 -->
    <div v-if="!jobStore.currentJob" class="history-section">
      <div class="history-header">
        <h3>📋 历史记录</h3>
        <el-button size="small" @click="loadHistory" :loading="jobStore.historyLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <el-table
        v-if="jobStore.jobHistory.length > 0"
        :data="jobStore.jobHistory"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="job_id" label="任务 ID" width="320">
          <template #default="{ row }">
            <span class="job-id">{{ row.job_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="100">
          <template #default="{ row }">
            {{ row.total_users || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'done'"
              size="small"
              type="primary"
              link
              @click="viewJob(row.job_id)"
            >
              查看摘要
            </el-button>
            <el-button
              v-if="row.status === 'done'"
              size="small"
              link
              @click="downloadJobCsv(row.job_id)"
            >
              下载 CSV
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无历史记录" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { Download, RefreshRight, Refresh } from '@element-plus/icons-vue'
import { useJobStore } from '@/stores/jobStore'
import { getDownloadUrl } from '@/api/job'
import UploadZone from '@/components/UploadZone.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import SummaryView from '@/components/SummaryView.vue'

const jobStore = useJobStore()

onMounted(() => {
  loadHistory()
})

function handleFileSelected(file: File) {
  jobStore.submitJob(file)
}

function downloadCsv() {
  const url = jobStore.getDownloadLink()
  if (url) {
    window.open(url, '_blank')
  }
}

function loadHistory() {
  jobStore.fetchHistory()
}

function viewJob(jobId: string) {
  jobStore.viewHistoryJob(jobId)
}

function downloadJobCsv(jobId: string) {
  window.open(getDownloadUrl(jobId), '_blank')
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

function getStatusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'done': return 'success'
    case 'running':
    case 'summarizing': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case 'queued': return '排队中'
    case 'running': return '处理中'
    case 'summarizing': return '生成摘要'
    case 'done': return '已完成'
    case 'failed': return '失败'
    default: return status
  }
}
</script>

<style scoped>
.home-page {
  max-width: 900px;
  margin: 0 auto;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.error-panel {
  text-align: center;
  padding: 40px;
}

.history-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.job-id {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}
</style>