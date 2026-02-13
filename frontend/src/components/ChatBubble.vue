<template>
  <view :class="['chat-bubble', message.role === 'user' ? 'bubble-right' : 'bubble-left']">
    <text class="bubble-content">{{ message.content }}</text>
    <text class="bubble-time">{{ formatTime(message.created_at) }}</text>
  </view>
</template>

<script setup lang="ts">
defineProps<{ message: { role: string; content: string; created_at: string } }>()

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped>
.chat-bubble {
  max-width: 75%;
  padding: 20rpx 28rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}
.bubble-left {
  align-self: flex-start;
  background-color: #f0f0f0;
}
.bubble-right {
  align-self: flex-end;
  background-color: #07c160;
  color: #fff;
}
.bubble-content {
  font-size: 28rpx;
  line-height: 1.6;
}
.bubble-time {
  font-size: 20rpx;
  opacity: 0.6;
  margin-top: 8rpx;
  display: block;
  text-align: right;
}
</style>
