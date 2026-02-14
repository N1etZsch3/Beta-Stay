<template>
  <view class="dashboard-page">
    <!-- Header -->
    <view class="header-section">
      <view class="header-content">
        <text class="app-title">BetaStay</text>
        <text class="app-subtitle">智能民宿定价助手</text>
      </view>
      <view class="header-bg"></view>
    </view>

    <!-- Content Container -->
    <view class="content-container">
      <!-- Stats Cards -->
      <view class="stats-row">
        <view class="stat-card">
          <text class="stat-value">{{ summary?.property_count ?? '-' }}</text>
          <text class="stat-label">房源数</text>
          <view class="stat-icon property-icon">🏠</view>
        </view>
        <view class="stat-card">
          <text class="stat-value">{{ summary?.recent_pricing_count ?? '-' }}</text>
          <text class="stat-label">30天定价</text>
          <view class="stat-icon pricing-icon">💰</view>
        </view>
        <view class="stat-card">
          <text class="stat-value">{{ summary?.feedback_count ?? '-' }}</text>
          <text class="stat-label">反馈数</text>
          <view class="stat-icon feedback-icon">📝</view>
        </view>
      </view>

      <!-- Quick Actions -->
      <view class="section-header">
        <text class="section-title">快捷操作</text>
      </view>
      <view class="quick-actions">
        <view class="action-card primary" @click="goChat">
          <view class="action-icon-wrapper">
            <text class="action-icon">💬</text>
          </view>
          <view class="action-content">
            <text class="action-title">智能对话</text>
            <text class="action-desc">获取定价建议</text>
          </view>
        </view>
        <view class="action-card" @click="goProperty">
           <view class="action-icon-wrapper secondary">
            <text class="action-icon">🏠</text>
          </view>
          <view class="action-content">
            <text class="action-title">房源管理</text>
            <text class="action-desc">管理我的房源</text>
          </view>
        </view>
      </view>
       <view class="quick-actions" style="margin-top: 20rpx;">
        <view class="action-card" @click="goHistory">
           <view class="action-icon-wrapper tertiary">
            <text class="action-icon">📊</text>
          </view>
          <view class="action-content">
            <text class="action-title">定价历史</text>
            <text class="action-desc">查看历史记录</text>
          </view>
        </view>
      </view>

      <!-- Property List -->
      <view class="section-header">
        <text class="section-title">我的房源</text>
        <text class="section-more" @click="goProperty">全部</text>
      </view>
      
      <view v-if="!summary?.properties?.length" class="empty-state">
        <view class="empty-icon">📂</view>
        <text class="empty-text">暂无房源数据</text>
        <button class="empty-btn" @click="goProperty">立即添加</button>
      </view>

      <view v-else class="property-list">
        <view v-for="prop in summary?.properties" :key="prop.id" class="property-card">
          <view class="prop-content">
            <view class="prop-main">
              <view class="prop-header-row">
                <text class="prop-name">{{ prop.name }}</text>
                <view class="prop-tag">{{ prop.room_type }}</view>
              </view>
              <text class="prop-address">{{ prop.address }}</text>
            </view>
            <view class="prop-price-block">
              <text class="price-label">最新建议价</text>
              <text v-if="prop.latest_suggested_price" class="price-value">
                <text class="currency">¥</text>{{ prop.latest_suggested_price }}
              </text>
              <text v-else class="no-price">暂无</text>
            </view>
          </view>
          <view class="prop-footer">
            <text class="prop-meta">{{ prop.area }}㎡</text>
            <text v-if="prop.latest_pricing_date" class="prop-date">更新于 {{ formatDate(prop.latest_pricing_date) }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useDashboardStore } from '../../stores/dashboard'

const dashboardStore = useDashboardStore()
const summary = computed(() => dashboardStore.summary)

onMounted(() => {
  dashboardStore.fetchSummary()
})

function goChat() {
  uni.switchTab({ url: '/pages/chat/index' })
}
function goProperty() {
  uni.switchTab({ url: '/pages/property/index' })
}
function goHistory() {
  uni.switchTab({ url: '/pages/history/index' })
}
function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped lang="scss">
.dashboard-page {
  min-height: 100%;
  box-sizing: border-box;
  padding-bottom: calc(var(--window-bottom) + 20rpx);
  background-color: $uni-bg-color-grey;
}

.header-section {
  position: relative;
  height: 360rpx;
  background: linear-gradient(135deg, $uni-color-primary 0%, $uni-color-primary-light-15 100%);
  border-bottom-left-radius: 40rpx;
  border-bottom-right-radius: 40rpx;
  overflow: hidden;
  padding: 88rpx 40rpx 0;
}

.header-content {
  position: relative;
  z-index: 2;
}

.app-title {
  display: block;
  font-size: 56rpx;
  font-weight: 800;
  color: #fff;
  letter-spacing: 2rpx;
  margin-bottom: 8rpx;
}

.app-subtitle {
  display: block;
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 300;
}

.header-bg {
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600rpx;
  height: 600rpx;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
  border-radius: 50%;
  z-index: 1;
}

.content-container {
  padding: 0 32rpx;
  margin-top: -100rpx;
  position: relative;
  z-index: 10;
  padding-bottom: 40rpx;
}

.stats-row {
  display: flex;
  gap: 20rpx;
  margin-bottom: 40rpx;
}

.stat-card {
  flex: 1;
  background: #fff;
  border-radius: $uni-border-radius-lg;
  padding: 32rpx 24rpx;
  position: relative;
  overflow: hidden;
  box-shadow: $uni-shadow-base;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-value {
  font-size: 40rpx;
  font-weight: 800;
  color: $uni-color-title;
  line-height: 1.2;
  margin-bottom: 8rpx;
}

.stat-label {
  font-size: 22rpx;
  color: $uni-text-color-grey;
}

.stat-icon {
  position: absolute;
  right: -10rpx;
  bottom: -10rpx;
  font-size: 60rpx;
  opacity: 0.1;
  transform: rotate(-15deg);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24rpx;
  padding: 0 8rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: $uni-color-title;
}

.section-more {
  font-size: 24rpx;
  color: $uni-color-primary;
}

.quick-actions {
  display: flex;
  gap: 20rpx;
}

.action-card {
  flex: 1;
  background: #fff;
  border-radius: $uni-border-radius-lg;
  padding: 24rpx;
  display: flex;
  align-items: center;
  gap: 20rpx;
  box-shadow: $uni-shadow-sm;
  transition: all 0.2s;
  
  &.primary {
    background: linear-gradient(135deg, $uni-color-primary-light-5 0%, $uni-color-primary 100%);
    
    .action-title { color: #fff; }
    .action-desc { color: rgba(255,255,255,0.8); }
    .action-icon-wrapper { background: rgba(255,255,255,0.2); }
  }
}

.action-icon-wrapper {
  width: 80rpx;
  height: 80rpx;
  background: $uni-bg-color-hover;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &.secondary { background: rgba($uni-color-success, 0.1); }
  &.tertiary { background: rgba($uni-color-warning, 0.1); }
}

.action-icon {
  font-size: 36rpx;
}

.action-content {
  flex: 1;
}

.action-title {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-color-title;
  display: block;
  margin-bottom: 4rpx;
}

.action-desc {
  font-size: 20rpx;
  color: $uni-text-color-grey;
  display: block;
}

.property-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.property-card {
  background: #fff;
  border-radius: $uni-border-radius-lg;
  padding: 32rpx;
  box-shadow: $uni-shadow-sm;
}

.prop-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
}

.prop-main {
  flex: 1;
  margin-right: 24rpx;
}

.prop-header-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.prop-name {
  font-size: 32rpx;
  font-weight: 700;
  color: $uni-color-title;
}

.prop-tag {
  font-size: 20rpx;
  color: $uni-color-primary;
  background: rgba($uni-color-primary, 0.1);
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.prop-address {
  font-size: 24rpx;
  color: $uni-text-color-grey;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
}

.prop-price-block {
  text-align: right;
  min-width: 140rpx;
}

.price-label {
  display: block;
  font-size: 20rpx;
  color: $uni-text-color-grey;
  margin-bottom: 4rpx;
}

.price-value {
  font-size: 36rpx;
  font-weight: 800;
  color: $uni-color-primary;
}

.currency {
  font-size: 24rpx;
  margin-right: 4rpx;
}

.no-price {
  font-size: 28rpx;
  color: $uni-text-color-disable;
  font-weight: 600;
}

.prop-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 24rpx;
  border-top: 1rpx solid $uni-border-color;
}

.prop-meta, .prop-date {
  font-size: 22rpx;
  color: $uni-text-color-placeholder;
}

.empty-state {
  background: #fff;
  border-radius: $uni-border-radius-lg;
  padding: 80rpx 40rpx;
  text-align: center;
  box-shadow: $uni-shadow-sm;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
  opacity: 0.5;
}

.empty-text {
  display: block;
  color: $uni-text-color-grey;
  font-size: 28rpx;
  margin-bottom: 32rpx;
}

.empty-btn {
  display: inline-block;
  background: $uni-color-primary;
  color: #fff;
  font-size: 28rpx;
  padding: 0 48rpx;
  height: 72rpx;
  line-height: 72rpx;
  border-radius: 36rpx;
}
</style>

