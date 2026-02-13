<template>
  <view :class="['chat-bubble-wrapper', message.role === 'user' ? 'wrapper-right' : 'wrapper-left']">
    <!-- AI Icon -->
    <view v-if="message.role === 'assistant'" class="ai-avatar">
      <text class="sparkle-icon">✨</text>
    </view>

    <view class="bubble-content-stack">
      <!-- User Message Bubble -->
      <view v-if="message.role === 'user'" class="user-bubble">
        <text class="bubble-text">{{ message.content }}</text>
      </view>

      <!-- AI Message Content (No Bubble, Mixed Text/Code) -->
      <view v-else class="ai-content">
        <!-- Thinking Section -->
        <view v-if="message.thinking" class="thinking-card">
          <view class="thinking-header" @click="showThinking = !showThinking">
            <text class="thinking-icon">💭</text>
            <text class="thinking-label">深度思考过程</text>
            <text class="thinking-arrow">{{ showThinking ? '▲' : '▼' }}</text>
          </view>
          <view v-if="showThinking" class="thinking-body">
            <text class="thinking-text">{{ message.thinking }}</text>
          </view>
        </view>

        <!-- Parsed Content -->
        <block v-for="(part, idx) in parsedContent" :key="idx">
          <!-- Text Part -->
          <text v-if="part.type === 'text'" class="ai-text" :selectable="true">{{ part.content }}</text>
          
          <!-- Code Part -->
          <view v-else-if="part.type === 'code'" class="code-block">
            <view class="code-header">
              <text class="code-lang">{{ part.lang || 'Code' }}</text>
              <view class="copy-btn" @click="copyCode(part.content)">
                 <text class="copy-icon">📋</text>
              </view>
            </view>
            <scroll-view scroll-x class="code-scroll">
               <text class="code-content" :selectable="true">{{ part.content }}</text>
            </scroll-view>
          </view>
        </block>

        <!-- Blinking Cursor -->
        <view v-if="isStreaming" class="cursor-blink"></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  message: {
    role: string
    content: string
    thinking?: string
    created_at: string
  }
  isStreaming?: boolean
}>()

const showThinking = ref(false)

// Simple markdown/code parser
const parsedContent = computed(() => {
  if (props.message.role === 'user') return [] // User msg handled simply
  
  const content = props.message.content || ''
  const parts = []
  const regex = /```(\w*)\n([\s\S]*?)```/g
  let lastIndex = 0
  let match
  
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'code', lang: match[1], content: match[2] })
    lastIndex = regex.lastIndex
  }
  
  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.slice(lastIndex) })
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content }]
})

function copyCode(code: string) {
  uni.setClipboardData({
    data: code,
    success: () => uni.showToast({ title: '已复制', icon: 'none' })
  })
}
</script>

<style scoped lang="scss">
.chat-bubble-wrapper {
  display: flex;
  margin-bottom: 40rpx;
  width: 100%;
}

.wrapper-left {
  justify-content: flex-start;
  align-items: flex-start;
  gap: 24rpx;
}

.wrapper-right {
  justify-content: flex-end;
}

/* Avatar */
.ai-avatar {
  width: 64rpx;
  height: 64rpx;
  background: white; /* or gradient */
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4rpx;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.05);
}

.sparkle-icon {
  font-size: 32rpx;
}

.bubble-content-stack {
  max-width: 85%;
  display: flex;
  flex-direction: column;
}

/* User Bubble */
.user-bubble {
  background: #2D3748; /* Dark Slate */
  color: #fff;
  padding: 24rpx 32rpx;
  border-radius: 36rpx;
  border-top-right-radius: 8rpx;
  box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1);
  font-size: 30rpx;
  line-height: 1.5;
}

/* AI Content */
.ai-content {
  color: $uni-text-color; /* Assume dark text on light bg, or light on dark if global theme changed */
  font-size: 30rpx;
  line-height: 1.6;
}

.ai-text {
  display: inline; /* allows cursor to sit next to it */
  white-space: pre-wrap;
}

/* Thinking Card */
.thinking-card {
  background: #F1F5F9;
  border-radius: 24rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
  border: 1rpx solid #E2E8F0;
}

.thinking-header {
  padding: 16rpx 24rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  background: rgba(255,255,255,0.5);
}

.thinking-icon { font-size: 28rpx; }
.thinking-label { font-size: 24rpx; font-weight: 600; color: #64748B; flex: 1; }
.thinking-arrow { font-size: 20rpx; color: #94A3B8; }

.thinking-body {
  padding: 24rpx;
  border-top: 1rpx solid #E2E8F0;
  background: #F8FAFC;
}

.thinking-text {
  font-size: 24rpx;
  color: #64748B;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* Code Block */
.code-block {
  margin: 16rpx 0;
  background: #1E293B; /* Dark Blue-Grey */
  border-radius: 16rpx;
  overflow: hidden;
  border: 1rpx solid #334155;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 24rpx;
  background: #0F172A;
  border-bottom: 1rpx solid #334155;
}

.code-lang {
  color: #94A3B8;
  font-size: 22rpx;
  font-family: monospace;
}

.copy-icon {
  color: #94A3B8;
  font-size: 28rpx;
}

.code-scroll {
  width: 100%;
}

.code-content {
  display: block;
  padding: 24rpx;
  color: #E2E8F0;
  font-family: monospace;
  font-size: 26rpx;
  white-space: pre;
}

/* Cursor */
.cursor-blink {
  display: inline-block;
  width: 14rpx;
  height: 32rpx;
  background: $uni-color-primary;
  margin-left: 4rpx;
  vertical-align: middle;
  border-radius: 4rpx;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
