<template>
  <view class="index-page">
    <view class="header">
      <text class="title">BetaStay</text>
      <text class="subtitle">智能民宿定价助手</text>
    </view>
    <view class="quick-actions">
      <view class="action-card" @click="navigateTo('/pages/chat/index')">
        <text class="action-title">智能对话</text>
        <text class="action-desc">与AI助手交流定价策略</text>
      </view>
      <view class="action-card" @click="navigateTo('/pages/property/index')">
        <text class="action-title">房源管理</text>
        <text class="action-desc">查看和管理房源信息</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
function navigateTo(url: string) {
  uni.switchTab({ url })
}
</script>

<style scoped>
.index-page {
  padding: 40rpx;
}
.header {
  text-align: center;
  margin-bottom: 60rpx;
  padding-top: 40rpx;
}
.title {
  font-size: 48rpx;
  font-weight: bold;
  display: block;
}
.subtitle {
  font-size: 28rpx;
  color: #999;
  margin-top: 12rpx;
  display: block;
}
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
.action-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.08);
}
.action-title {
  font-size: 32rpx;
  font-weight: bold;
  display: block;
}
.action-desc {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
</style>
