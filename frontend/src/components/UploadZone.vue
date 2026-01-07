<template>
  <div
    class="upload-zone"
    :class="{ 'is-dragover': isDragover }"
    @dragover.prevent="isDragover = true"
    @dragleave.prevent="isDragover = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".csv"
      style="display: none"
      @change="handleFileChange"
    />
    <div class="upload-content">
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <h3>拖拽 CSV 文件到这里</h3>
      <p>或点击选择文件</p>
      <p class="hint">CSV 需包含 username 列（X/Twitter 用户名）</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits<{
  (e: 'file-selected', file: File): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragover = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    validateAndEmit(file)
  }
}

function handleDrop(e: DragEvent) {
  isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    validateAndEmit(file)
  }
}

function validateAndEmit(file: File) {
  if (!file.name.endsWith('.csv')) {
    ElMessage.error('请上传 CSV 文件')
    return
  }
  emit('file-selected', file)
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.upload-zone:hover {
  border-color: #1da1f2;
  background: #f8fbff;
}

.upload-zone.is-dragover {
  border-color: #1da1f2;
  background: #e8f5fe;
}

.upload-content {
  color: #606266;
}

.upload-icon {
  font-size: 48px;
  color: #1da1f2;
  margin-bottom: 16px;
}

.upload-content h3 {
  font-size: 18px;
  margin-bottom: 8px;
  color: #303133;
}

.upload-content p {
  margin: 4px 0;
  font-size: 14px;
}

.upload-content .hint {
  color: #909399;
  font-size: 12px;
  margin-top: 12px;
}
</style>
