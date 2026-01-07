<template>
  <div class="summary-view">
    <h2 class="summary-title">📋 智能摘要</h2>
    <div class="summary-content" v-html="renderedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
}>()

const renderedContent = computed(() => {
  if (!props.content) return ''
  return marked(props.content, { breaks: true })
})
</script>

<style scoped>
.summary-view {
  background: white;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.summary-title {
  font-size: 20px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
  color: #303133;
}

.summary-content {
  line-height: 1.8;
  color: #303133;
}

.summary-content :deep(h1),
.summary-content :deep(h2),
.summary-content :deep(h3) {
  margin-top: 24px;
  margin-bottom: 12px;
  color: #1f2937;
}

.summary-content :deep(h2) {
  font-size: 18px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.summary-content :deep(h3) {
  font-size: 16px;
}

.summary-content :deep(p) {
  margin: 12px 0;
}

.summary-content :deep(ul),
.summary-content :deep(ol) {
  padding-left: 24px;
  margin: 12px 0;
}

.summary-content :deep(li) {
  margin: 6px 0;
}

.summary-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}

.summary-content :deep(th),
.summary-content :deep(td) {
  border: 1px solid #ebeef5;
  padding: 10px 12px;
  text-align: left;
}

.summary-content :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.summary-content :deep(tr:nth-child(even)) {
  background: #fafafa;
}

.summary-content :deep(a) {
  color: #1da1f2;
  text-decoration: none;
}

.summary-content :deep(a:hover) {
  text-decoration: underline;
}

.summary-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.summary-content :deep(pre) {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.summary-content :deep(blockquote) {
  border-left: 4px solid #1da1f2;
  padding-left: 16px;
  margin: 16px 0;
  color: #606266;
}
</style>
