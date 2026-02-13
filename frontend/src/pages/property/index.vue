<template>
  <view class="property-page">
    <!-- Header Actions -->
    <view class="header-bar">
      <view class="page-title-block">
        <text class="page-title">房源管理</text>
        <text class="page-count">共 {{ propertyStore.properties.length }} 套</text>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="propertyStore.loading" class="loading-state">
      <view class="loading-spinner"></view>
      <text class="loading-text">加载中...</text>
    </view>

    <!-- Empty -->
    <view v-else-if="!propertyStore.properties.length" class="empty-state">
      <view class="empty-icon">🏠</view>
      <text class="empty-text">您还没有添加任何房源</text>
      <text class="empty-subtext">添加房源后，AI将为您提供智能定价建议</text>
      <button class="add-btn-large" @click="goAdd">立即添加房源</button>
    </view>

    <!-- Property List -->
    <view v-else class="property-list">
      <view
        v-for="prop in propertyStore.properties"
        :key="prop.id"
        class="property-card"
        @click="goEdit(prop.id)"
      >
        <view class="card-main">
          <view class="card-header">
            <view class="header-left">
              <text class="card-name">{{ prop.name }}</text>
              <view class="card-tag">{{ prop.room_type }}</view>
            </view>
            <view class="header-right">
              <text class="area-text">{{ prop.area }}㎡</text>
            </view>
          </view>
          
          <view class="card-address-row">
            <text class="address-icon">📍</text>
            <text class="card-address">{{ prop.address }}</text>
          </view>

          <view class="card-tags" v-if="prop.expected_return_rate || prop.vacancy_tolerance">
            <view v-if="prop.expected_return_rate" class="info-tag green">
              <text class="tag-label">期望收益</text>
              <text class="tag-value">{{ (prop.expected_return_rate * 100).toFixed(0) }}%</text>
            </view>
            <view v-if="prop.vacancy_tolerance" class="info-tag blue">
              <text class="tag-label">空置容忍</text>
              <text class="tag-value">{{ (prop.vacancy_tolerance * 100).toFixed(0) }}%</text>
            </view>
          </view>
        </view>

        <view class="card-footer">
          <view class="price-range">
            <text class="price-label">定价范围</text>
             <text v-if="prop.min_price" class="price-val">¥{{ prop.min_price }} - ¥{{ prop.max_price }}</text>
             <text v-else class="price-placeholder">未设置</text>
          </view>
          <view class="action-buttons">
            <view class="icon-btn delete" @click.stop="handleDelete(prop.id, prop.name)">
              <text class="btn-icon">🗑️</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- Floating Add Button -->
    <view class="fab-btn" @click="goAdd">
      <text class="fab-icon">+</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'

const propertyStore = usePropertyStore()

onMounted(() => {
  propertyStore.fetchList()
})

function goAdd() {
  uni.navigateTo({ url: '/pages/property/form' })
}

function goEdit(id: number) {
  uni.navigateTo({ url: `/pages/property/form?id=${id}` })
}

function handleDelete(id: number, name: string) {
  uni.showModal({
    title: '确认删除',
    content: `确定要删除房源"${name}"吗？\n删除后无法恢复。`,
    confirmColor: '#EF4444',
    success: async (res) => {
      if (res.confirm) {
        await propertyStore.remove(id)
        uni.showToast({ title: '已删除', icon: 'success' })
      }
    },
  })
}
</script>

<style scoped lang="scss">
.property-page {
  padding: 32rpx;
  background-color: $uni-bg-color-grey;
  min-height: 100%;
  box-sizing: border-box;
  padding-bottom: calc(var(--window-bottom) + 120rpx);
}

.header-bar {
  margin-bottom: 32rpx;
  padding: 0 8rpx;
}

.page-title {
  font-size: 44rpx;
  font-weight: 800;
  color: $uni-color-title;
  margin-right: 16rpx;
}

.page-count {
  font-size: 24rpx;
  color: $uni-text-color-grey;
  background: #E2E8F0;
  padding: 4rpx 12rpx;
  border-radius: 20rpx;
}

.property-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.property-card {
  background: #fff;
  border-radius: $uni-border-radius-lg;
  overflow: hidden;
  box-shadow: $uni-shadow-base;
  transition: transform 0.1s;
  
  &:active {
    transform: scale(0.98);
  }
}

.card-main {
  padding: 32rpx 32rpx 24rpx;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16rpx;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex: 1;
}

.card-name {
  font-size: 34rpx;
  font-weight: 700;
  color: $uni-color-title;
  line-height: 1.4;
}

.card-tag {
  font-size: 20rpx;
  color: $uni-color-primary;
  background: rgba($uni-color-primary, 0.1);
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  white-space: nowrap;
}

.area-text {
  font-size: 24rpx;
  color: $uni-text-color-grey;
  font-weight: 500;
}

.card-address-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 24rpx;
}

.address-icon {
  font-size: 24rpx;
  opacity: 0.6;
}

.card-address {
  font-size: 26rpx;
  color: $uni-text-color-secondary;
  line-height: 1.4;
}

.card-tags {
  display: flex;
  gap: 16rpx;
}

.info-tag {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 6rpx 12rpx;
  border-radius: 8rpx;
  
  &.green { background: #ECFDF5; .tag-label, .tag-value { color: #059669; } }
  &.blue { background: #EFF6FF; .tag-label, .tag-value { color: #2563EB; } }
}

.tag-label {
  font-size: 20rpx;
  opacity: 0.8;
}

.tag-value {
  font-size: 20rpx;
  font-weight: 700;
}

.card-footer {
  background: #F8FAFC;
  padding: 20rpx 32rpx;
  border-top: 1rpx solid $uni-border-color;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price-label {
  font-size: 22rpx;
  color: $uni-text-color-grey;
  margin-right: 12rpx;
}

.price-val {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-color-title;
}

.price-placeholder {
  font-size: 24rpx;
  color: $uni-text-color-disable;
}

.icon-btn {
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  
  &.delete {
    background: #FEF2F2;
    .btn-icon { color: #EF4444; font-size: 28rpx; }
    &:active { background: #FEE2E2; }
  }
}

.fab-btn {
  position: fixed;
  right: 40rpx;
  bottom: 200rpx;
  width: 110rpx;
  height: 110rpx;
  background: $uni-color-primary;
  border-radius: 50%;
  box-shadow: 0 8rpx 20rpx rgba(26, 75, 156, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: transform 0.2s;
  
  &:active { transform: scale(0.9); }
}

.fab-icon {
  font-size: 60rpx;
  color: #fff;
  line-height: 1;
  font-weight: 300;
  margin-top: -8rpx;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 100rpx;
}

.loading-spinner {
  width: 40rpx;
  height: 40rpx;
  border: 4rpx solid $uni-border-color;
  border-top-color: $uni-color-primary;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 24rpx;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 26rpx;
  color: $uni-text-color-grey;
}

.empty-icon {
  font-size: 100rpx;
  margin-bottom: 32rpx;
  opacity: 0.5;
}

.empty-text {
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-color-title;
  margin-bottom: 12rpx;
}

.empty-subtext {
  font-size: 26rpx;
  color: $uni-text-color-grey;
  margin-bottom: 48rpx;
}

.add-btn-large {
  background: $uni-color-primary;
  color: #fff;
  font-size: 30rpx;
  font-weight: 600;
  padding: 0 60rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  box-shadow: 0 4rpx 12rpx rgba(26, 75, 156, 0.3);
  
  &:active { transform: translateY(2rpx); }
}
</style>

