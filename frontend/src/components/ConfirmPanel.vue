<template>
  <view v-if="visible" class="confirm-overlay">
    <view class="confirm-panel">
      <text class="confirm-title">数据确认</text>
      <scroll-view scroll-y class="confirm-body">
        <view v-for="(value, key) in data" :key="key" class="confirm-row">
          <text class="confirm-label">{{ key }}</text>
          <text class="confirm-value">{{ value }}</text>
        </view>
      </scroll-view>
      <view class="confirm-actions">
        <button class="btn-cancel" @click="$emit('cancel')">取消</button>
        <button class="btn-confirm" @click="$emit('confirm')">确认入库</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean; data: Record<string, any> }>()
defineEmits<{ confirm: []; cancel: [] }>()
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: flex-end;
  z-index: 999;
}
.confirm-panel {
  width: 100%;
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 40rpx;
  max-height: 70vh;
}
.confirm-title {
  font-size: 32rpx;
  font-weight: bold;
  margin-bottom: 20rpx;
}
.confirm-body {
  max-height: 50vh;
}
.confirm-row {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eee;
}
.confirm-label { color: #666; font-size: 28rpx; }
.confirm-value { color: #333; font-size: 28rpx; }
.confirm-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 30rpx;
}
.btn-cancel {
  flex: 1;
  background: #f5f5f5;
  color: #666;
}
.btn-confirm {
  flex: 1;
  background: #07c160;
  color: #fff;
}
</style>
