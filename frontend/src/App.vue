<template>
  <div class="app-container">
    <el-container>
      <el-header class="app-header">
        <div class="header-content">
          <h1 class="app-title">X-Feed Digest</h1>
          <span class="app-subtitle">Twitter/X 关注动态聚合与智能摘要</span>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #1da1f2 0%, #0d8ecf 100%);
  color: white;
  display: flex;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.app-title {
  font-size: 24px;
  font-weight: 600;
}

.app-subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.el-main {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
