<template>
  <view :class="['chat-bubble-wrapper', message.role === 'user' ? 'wrapper-right' : 'wrapper-left']">
    <!-- Avatar (Optional, can add later) -->
    
    <view class="bubble-container">
      <!-- Thinking toggle (assistant only) -->
      <view
        v-if="message.role === 'assistant' && message.thinking"
        class="thinking-section"
      >
        <view class="thinking-toggle" @click="showThinking = !showThinking">
          <text class="thinking-icon">💭</text>
          <text class="thinking-label">{{ showThinking ? '收起思考过程' : 'AI思考过程' }}</text>
        </view>
        <view v-if="showThinking" class="thinking-content">
          <text class="thinking-text">{{ message.thinking }}</text>
        </view>
      </view>

      <!-- Main content -->
      <view :class="['bubble-body', message.role === 'user' ? 'body-right' : 'body-left']">
        <text class="bubble-text">{{ message.content }}</text>
      </view>
      
      <!-- Time -->
      <text class="bubble-time">{{ formatTime(message.created_at) }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  message: {
    role: string
    content: string
    thinking?: string
    created_at: string
  }
}>()

const showThinking = ref(false)

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped lang="scss">
.chat-bubble-wrapper {
  display: flex;
  margin-bottom: 32rpx;
  width: 100%;
}

.wrapper-left {
  justify-content: flex-start;
}

.wrapper-right {
  justify-content: flex-end;
}

.bubble-container {
  max-width: 80%;
  display: flex;
  flex-direction: column;
}

.wrapper-right .bubble-container {
  align-items: flex-end;
}

.wrapper-left .bubble-container {
  align-items: flex-start;
}

.bubble-body {
  padding: 20rpx 28rpx;
  border-radius: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  position: relative;
  word-wrap: break-word;
}

.body-left {
  background: #fff;
  color: $uni-text-color;
  border-top-left-radius: 4rpx;
}

.body-right {
  background: $uni-color-primary;
  color: #fff;
  border-top-right-radius: 4rpx;
}

.bubble-text {
  font-size: 30rpx;
  line-height: 1.5;
  white-space: pre-wrap;
}

.bubble-time {
  font-size: 20rpx;
  color: $uni-text-color-placeholder;
  margin-top: 8rpx;
  padding: 0 8rpx;
}

/* Thinking Section */
.thinking-section {
  margin-bottom: 12rpx;
  background: #F8FAFC;
  border-radius: 16rpx;
  padding: 12rpx 16rpx;
  border: 1rpx solid #E2E8F0;
  width: 100%;
  box-sizing: border-box;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.thinking-icon {
  font-size: 24rpx;
}

.thinking-label {
  font-size: 22rpx;
  color: $uni-text-color-grey;
}

.thinking-content {
  margin-top: 12rpx;
  padding-top: 12rpx;
  border-top: 1rpx dashed #E2E8F0;
}

.thinking-text {
  font-size: 22rpx;
  color: $uni-text-color-grey;
  line-height: 1.4;
  white-space: pre-wrap;
}
</style>

