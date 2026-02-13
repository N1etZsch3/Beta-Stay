<template>
  <view class="history-page">
    <view class="page-container">
      <!-- Header -->
      <view class="header-block">
        <text class="page-title">定价历史</text>
        <view class="selector-wrapper">
          <picker :range="propertyNames" @change="onPropertyChange" class="prop-picker">
            <view class="picker-inner">
              <text class="picker-label">当前房源</text>
              <view class="picker-value-row">
                <text class="picker-value">{{ selectedPropertyName || '点击选择房源' }}</text>
                <text class="picker-icon">▼</text>
              </view>
            </view>
          </picker>
        </view>
      </view>

      <!-- Loading -->
      <view v-if="historyStore.loading" class="loading-state">
        <view class="loading-spinner"></view>
        <text class="loading-text">加载历史记录...</text>
      </view>

      <!-- Empty States -->
      <view v-else-if="!selectedPropertyId" class="empty-state">
        <view class="empty-icon">👆</view>
        <text class="empty-text">请在上方选择一个房源</text>
        <text class="empty-subtext">查看该房源的历史定价记录</text>
      </view>

      <view v-else-if="!historyStore.pricingRecords.length" class="empty-state">
        <view class="empty-icon">📂</view>
        <text class="empty-text">暂无定价记录</text>
        <text class="empty-subtext">该房源尚未进行过智能定价</text>
      </view>

      <!-- Pricing Records Timeline -->
      <view v-else class="timeline-list">
        <view
          v-for="(record, index) in historyStore.pricingRecords"
          :key="record.id"
          class="timeline-item"
        >
          <!-- Date Header (stick to top if needed, but simple for now) -->
          <view class="timeline-date-badge" v-if="shouldShowDate(index)">
            {{ formatDateHeader(record.target_date) }}
          </view>
          
          <view class="record-card">
            <view class="card-header">
              <view class="header-left">
                <text class="target-date-label">目标日期</text>
                <text class="target-date-val">{{ formatTargetDate(record.target_date) }}</text>
              </view>
              <text class="calc-time">{{ formatTime(record.created_at) }} 计算</text>
            </view>

            <view class="price-grid">
              <view class="price-box conservative">
                <text class="p-label">保守</text>
                <text class="p-val">¥{{ record.conservative_price }}</text>
              </view>
              <view class="price-box suggested">
                <text class="p-label">建议</text>
                <text class="p-val">¥{{ record.suggested_price }}</text>
                <view class="recommend-badge">推荐</view>
              </view>
              <view class="price-box aggressive">
                <text class="p-label">激进</text>
                <text class="p-val">¥{{ record.aggressive_price }}</text>
              </view>
            </view>

            <!-- Associated Feedback -->
            <view class="feedback-section" v-if="getFeedbackForRecord(record.id).length">
              <view v-for="fb in getFeedbackForRecord(record.id)" :key="fb.id" class="feedback-item">
                <view :class="['fb-badge', fb.feedback_type]">
                  {{ feedbackLabel(fb.feedback_type) }}
                </view>
                <view class="fb-content">
                  <text v-if="fb.actual_price" class="fb-price">定价 ¥{{ fb.actual_price }}</text>
                  <text v-if="fb.note" class="fb-note">"{{ fb.note }}"</text>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'
import { useHistoryStore } from '../../stores/history'

const propertyStore = usePropertyStore()
const historyStore = useHistoryStore()
const selectedPropertyId = ref<number | null>(null)

const propertyNames = computed(() => propertyStore.properties.map(p => p.name))
const selectedPropertyName = computed(() => {
  if (!selectedPropertyId.value) return ''
  return propertyStore.properties.find(p => p.id === selectedPropertyId.value)?.name || ''
})

onMounted(() => {
  propertyStore.fetchList()
})

async function onPropertyChange(e: any) {
  const idx = e.detail.value
  const prop = propertyStore.properties[idx]
  if (prop) {
    selectedPropertyId.value = prop.id
    await historyStore.fetchByProperty(prop.id)
  }
}

function getFeedbackForRecord(recordId: number) {
  return historyStore.feedbacks.filter(f => f.pricing_record_id === recordId)
}

function feedbackLabel(type: string) {
  const map: Record<string, string> = { adopted: '已采纳', rejected: '已拒绝', adjusted: '已调整' }
  return map[type] || type
}

function shouldShowDate(index: number) {
  if (index === 0) return true
  const curr = historyStore.pricingRecords[index]
  const prev = historyStore.pricingRecords[index - 1]
  return curr.target_date !== prev.target_date
}

function formatDateHeader(dateStr: string) {
  // Simple format: "2023-10-27" -> "10月27日"
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatTargetDate(dateStr: string) {
  const d = new Date(dateStr)
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}/${d.getDate()} 周${weekDays[d.getDay()]}`
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped lang="scss">
.history-page {
  min-height: 100%;
  box-sizing: border-box;
  padding-bottom: calc(var(--window-bottom) + 20rpx);
  background-color: $uni-bg-color-grey;
}

.page-container {
  padding: 32rpx;
}

.header-block {
  margin-bottom: 32rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: 800;
  color: $uni-color-title;
  margin-bottom: 24rpx;
  display: block;
}

.selector-wrapper {
  background: #fff;
  border-radius: $uni-border-radius-lg;
  box-shadow: $uni-shadow-sm;
  overflow: hidden;
}

.picker-inner {
  padding: 24rpx 32rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.picker-label {
  font-size: 26rpx;
  color: $uni-text-color-grey;
}

.picker-value-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.picker-value {
  font-size: 30rpx;
  font-weight: 600;
  color: $uni-color-primary;
}

.picker-icon {
  font-size: 20rpx;
  color: $uni-text-color-placeholder;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
}

.timeline-date-badge {
  align-self: center;
  background: #E2E8F0;
  color: $uni-text-color-grey;
  font-size: 24rpx;
  padding: 8rpx 24rpx;
  border-radius: 20rpx;
  margin-bottom: 16rpx;
  font-weight: 500;
}

.record-card {
  background: #fff;
  border-radius: $uni-border-radius-lg;
  padding: 32rpx;
  box-shadow: $uni-shadow-base;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
  padding-bottom: 24rpx;
  border-bottom: 1rpx solid $uni-bg-color-hover;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.target-date-label {
  font-size: 22rpx;
  color: $uni-text-color-placeholder;
  margin-bottom: 4rpx;
}

.target-date-val {
  font-size: 32rpx;
  font-weight: 700;
  color: $uni-color-title;
}

.calc-time {
  font-size: 22rpx;
  color: $uni-text-color-placeholder;
}

.price-grid {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 8rpx;
}

.price-box {
  flex: 1;
  background: $uni-bg-color-hover;
  border-radius: 12rpx;
  padding: 20rpx 12rpx;
  text-align: center;
  position: relative;
  
  &.conservative {
    .p-val { color: $uni-color-success; }
  }
  
  &.suggested {
    background: #EFF6FF;
    border: 2rpx solid rgba($uni-color-primary, 0.1);
    .p-val { color: $uni-color-primary; }
    .p-label { color: $uni-color-primary; opacity: 0.8; }
  }
  
  &.aggressive {
    .p-val { color: $uni-color-warning; }
  }
}

.p-label {
  font-size: 22rpx;
  color: $uni-text-color-grey;
  display: block;
  margin-bottom: 8rpx;
}

.p-val {
  font-size: 32rpx;
  font-weight: 700;
  display: block;
}

.recommend-badge {
  position: absolute;
  top: -12rpx;
  left: 50%;
  transform: translateX(-50%);
  background: $uni-color-primary;
  color: #fff;
  font-size: 18rpx;
  padding: 4rpx 12rpx;
  border-radius: 10rpx;
  white-space: nowrap;
}

.feedback-section {
  margin-top: 24rpx;
  background: #F8FAFC;
  border-radius: 12rpx;
  padding: 16rpx;
}

.feedback-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.fb-badge {
  font-size: 20rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  
  &.adopted { background: #D1FAE5; color: #059669; }
  &.rejected { background: #FEE2E2; color: #DC2626; }
  &.adjusted { background: #FEF3C7; color: #D97706; }
}

.fb-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex-wrap: wrap;
}

.fb-price {
  font-size: 24rpx;
  color: $uni-color-title;
  font-weight: 600;
}

.fb-note {
  font-size: 24rpx;
  color: $uni-text-color-grey;
  font-style: italic;
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
  font-size: 80rpx;
  margin-bottom: 24rpx;
  opacity: 0.5;
}

.empty-text {
  font-size: 30rpx;
  font-weight: 600;
  color: $uni-color-title;
  margin-bottom: 12rpx;
}

.empty-subtext {
  font-size: 24rpx;
  color: $uni-text-color-grey;
}
</style>

