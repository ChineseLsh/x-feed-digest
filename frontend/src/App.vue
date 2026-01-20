<template>
  <div class="app-container">
    <el-container>
      <el-header class="app-header">
        <div class="header-content">
          <h1 class="app-title">X-Feed Digest</h1>
          <span class="app-subtitle">Twitter/X 关注动态聚合与智能摘要</span>
        </div>
        <nav class="header-nav">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            首页
          </router-link>
          <router-link to="/subscriptions" class="nav-link" :class="{ active: $route.path === '/subscriptions' }">
            定时订阅
          </router-link>
        </nav>
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
  justify-content: space-between;
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

.header-nav {
  display: flex;
  gap: 8px;
}

.nav-link {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
  color: white;
  background: rgba(255, 255, 255, 0.2);
}

.el-main {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>