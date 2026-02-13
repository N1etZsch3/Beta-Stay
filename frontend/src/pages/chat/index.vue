<template>
  <view class="chat-page">
    <!-- Message area -->
    <scroll-view
      scroll-y
      class="message-list"
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view class="list-padding">
        <!-- Empty State -->
        <view v-if="chatStore.messages.length === 0" class="empty-state">
           <view class="welcome-icon">✨</view>
          <text class="welcome-title">你好, 我是 BetaStay 助手</text>
          <text class="welcome-desc">我可以帮你分析房源定价、管理房源信息，或回答民宿运营相关问题。</text>
          
          <view class="suggestion-chips">
            <view class="chip" @click="quickAsk('帮我分析一下我的房源价格')">
              <text class="chip-icon">💰</text>
              <text>价格分析</text>
            </view>
            <view class="chip" @click="quickAsk('最近周边的民宿行情怎么样？')">
              <text class="chip-icon">📊</text>
              <text>市场行情</text>
            </view>
            <view class="chip" @click="quickAsk('如何提高入住率？')">
              <text class="chip-icon">📈</text>
              <text>运营建议</text>
            </view>
          </view>
        </view>

        <!-- Messages -->
        <ChatBubble
          v-for="(msg, idx) in chatStore.messages"
          :key="idx"
          :message="msg"
          :is-streaming="idx === chatStore.messages.length - 1 && chatStore.loading"
        />

        <!-- Loading / Thinking Indicator (Implicit in last message now, but keep fallback) -->
        <view v-if="chatStore.loading && chatStore.messages.length === 0" class="status-tip">
           <text>AI正在准备...</text>
        </view>

        <!-- Bottom Spacer -->
        <view class="scroll-bottom-spacer" />
      </view>
    </scroll-view>

    <!-- Floating Input Area -->
    <view class="input-section">
      <view class="input-card">
        <view class="icon-btn-left">
          <text class="action-icon">⊕</text>
        </view>
        
        <input
          v-model="inputText"
          class="chat-input"
          placeholder="问点什么..."
          confirm-type="send"
          @confirm="handleSend"
          :disabled="chatStore.loading"
          placeholder-style="color: #94A3B8;"
        />
        
        <view class="right-actions">
           <view v-if="!inputText" class="icon-btn-right">
             <text class="action-icon">🎤</text>
           </view>
           <view 
             v-else
             :class="['send-btn', { disabled: chatStore.loading }]"
             @click="handleSend"
           >
            <text class="send-icon">↑</text>
           </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTop = ref(0)

// Auto-scroll
watch(
  () => [chatStore.messages.length, chatStore.messages.at(-1)?.content],
  async () => {
    await nextTick()
    scrollToBottom()
  },
  { deep: true }
)

// Also scroll on thinking state change
watch(() => chatStore.thinking, async () => {
  await nextTick()
  scrollToBottom()
})

function scrollToBottom() {
  scrollTop.value = scrollTop.value === 99998 ? 99999 : 99998
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  inputText.value = ''
  try {
    await chatStore.sendMessage(text)
  } catch {
    // Error handling
  }
}

function quickAsk(text: string) {
  inputText.value = text
  handleSend()
}
</script>

<style scoped lang="scss">
.chat-page {
  background-color: $uni-bg-color-grey;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  flex: 1;
  height: 0; 
  width: 100%;
}

.list-padding {
  padding: 32rpx 24rpx;
  padding-bottom: 40rpx;
}

.scroll-bottom-spacer {
  height: 180rpx; /* Space for floating input */
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100rpx 40rpx;
}

.welcome-icon {
  font-size: 80rpx;
  background: white;
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 40rpx;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.05);
}

.welcome-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #1E293B; /* Slate 800 */
  margin-bottom: 16rpx;
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-desc {
  font-size: 28rpx;
  color: #64748B;
  text-align: center;
  line-height: 1.6;
  margin-bottom: 80rpx;
  max-width: 600rpx;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 24rpx;
  width: 100%;
}

.chip {
  background: #fff;
  border: 1rpx solid #E2E8F0;
  padding: 20rpx 32rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  color: #334155;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.02);
  display: flex;
  align-items: center;
  gap: 12rpx;
  transition: all 0.2s;
  
  &:active {
    background: #F1F5F9;
    transform: scale(0.98);
  }
}

.chip-icon { font-size: 32rpx; }

/* Floating Input Section */
.input-section {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24rpx 32rpx;
  padding-bottom: calc(24rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
  background: linear-gradient(to top, rgba(248,250,252, 1) 80%, rgba(248,250,252, 0) 100%);
  z-index: 100;
}

.input-card {
  background: #fff;
  border-radius: 48rpx;
  padding: 16rpx 16rpx 16rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.08);
  border: 1rpx solid #E2E8F0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:focus-within {
    box-shadow: 0 12rpx 32rpx rgba(26, 75, 156, 0.1);
    border-color: rgba(26, 75, 156, 0.2);
    transform: translateY(-2rpx);
  }
}

.icon-btn-left, .icon-btn-right {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F1F5F9;
  color: #475569;
}

.action-icon {
  font-size: 36rpx;
  font-weight: 300;
}

.chat-input {
  flex: 1;
  height: 48rpx;
  font-size: 32rpx;
  color: #1E293B;
  min-height: 48rpx;
}

.send-btn {
  width: 72rpx;
  height: 72rpx;
  background: $uni-color-primary;
  border-radius: 36rpx; /* Pill/Circle */
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  
  &.disabled {
    background: #CBD5E1;
  }
  
  &:active:not(.disabled) {
    transform: scale(0.9);
  }
}

.send-icon {
  color: #fff;
  font-size: 36rpx;
  font-weight: bold;
}

.status-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20rpx;
  font-size: 24rpx;
  color: #94A3B8;
}
</style>
