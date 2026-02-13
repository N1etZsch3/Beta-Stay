<template>
  <view class="chat-page">
    <!-- Header (Optional, if not using native nav bar) -->
    <!-- <view class="chat-header">...</view> -->

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
           <view class="welcome-icon">👋</view>
          <text class="welcome-title">你好！我是BetaStay助手</text>
          <text class="welcome-desc">我可以帮你分析房源定价、管理房源信息，或回答民宿运营相关问题。</text>
          
          <view class="suggestion-chips">
            <view class="chip" @click="quickAsk('帮我分析一下我的房源价格')">💰 价格分析</view>
            <view class="chip" @click="quickAsk('最近周边的民宿行情怎么样？')">📊 市场行情</view>
            <view class="chip" @click="quickAsk('如何提高入住率？')">📈 运营建议</view>
          </view>
        </view>

        <!-- Messages -->
        <ChatBubble
          v-for="(msg, idx) in chatStore.messages"
          :key="idx"
          :message="msg"
        />

        <!-- Loading / Thinking -->
        <view v-if="chatStore.thinking" class="status-tip">
          <view class="typing-indicator">
            <view class="dot"></view>
            <view class="dot"></view>
            <view class="dot"></view>
          </view>
          <text>AI正在深度思考...</text>
        </view>
        <view v-else-if="chatStore.loading && !chatStore.thinking" class="status-tip">
          <text>AI正在输入...</text>
        </view>

        <!-- Bottom Spacer -->
        <view class="scroll-bottom-spacer" />
      </view>
    </scroll-view>

    <!-- Input area -->
    <view class="input-container">
      <view class="input-wrapper">
        <input
          v-model="inputText"
          class="chat-input"
          placeholder="问点什么..."
          confirm-type="send"
          @confirm="handleSend"
          :disabled="chatStore.loading"
          placeholder-style="color: #94A3B8;"
        />
        <view 
          :class="['send-btn', { disabled: !inputText.trim() || chatStore.loading }]"
          @click="handleSend"
        >
          <text class="send-icon">↑</text>
        </view>
      </view>
    </view>

    <!-- Confirm panel -->
    <ConfirmPanel
      :visible="showConfirm"
      :data="confirmData"
      @confirm="handleConfirm"
      @cancel="showConfirm = false"
    />
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'
import ConfirmPanel from '../../components/ConfirmPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTop = ref(0)
const showConfirm = ref(false)
const confirmData = ref<Record<string, any>>({})

// Auto-scroll
watch(
  () => chatStore.messages.map(m => m.content).join(''),
  async () => {
    await nextTick()
    scrollToBottom()
  },
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

function handleConfirm() {
  showConfirm.value = false
  // TODO: call confirm API
}
</script>

<style scoped lang="scss">
.chat-page {
  background-color: $uni-bg-color-grey;
  height: 100%; /* Changed from 100vh */
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
}

.scroll-bottom-spacer {
  height: 40rpx;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100rpx 40rpx;
}

.welcome-icon {
  font-size: 80rpx;
  margin-bottom: 32rpx;
}

.welcome-title {
  font-size: 36rpx;
  font-weight: 700;
  color: $uni-color-title;
  margin-bottom: 16rpx;
}

.welcome-desc {
  font-size: 28rpx;
  color: $uni-text-color-grey;
  text-align: center;
  line-height: 1.6;
  margin-bottom: 60rpx;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20rpx;
  width: 100%;
}

.chip {
  background: #fff;
  border: 1rpx solid $uni-border-color;
  padding: 16rpx 32rpx;
  border-radius: 40rpx;
  font-size: 26rpx;
  color: $uni-text-color;
  box-shadow: $uni-shadow-sm;
  transition: all 0.2s;
  
  &:active {
    background: $uni-bg-color-hover;
    transform: scale(0.98);
  }
}

.status-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  padding: 24rpx;
  color: $uni-text-color-placeholder;
  font-size: 24rpx;
}

.typing-indicator {
  display: flex;
  gap: 8rpx;
}

.dot {
  width: 8rpx;
  height: 8rpx;
  background: $uni-text-color-placeholder;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
  
  &:nth-child(1) { animation-delay: -0.32s; }
  &:nth-child(2) { animation-delay: -0.16s; }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-container {
  background: #fff;
  padding: 20rpx 24rpx;
  padding-bottom: calc(20rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid $uni-border-color;
  box-shadow: 0 -4rpx 12rpx rgba(0,0,0,0.03);
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: $uni-bg-color-hover;
  border-radius: 44rpx;
  padding: 8rpx 8rpx 8rpx 32rpx;
  border: 1rpx solid transparent;
  transition: border-color 0.2s;
  
  &:focus-within {
    border-color: rgba($uni-color-primary, 0.3);
    background: #fff;
  }
}

.chat-input {
  flex: 1;
  height: 72rpx;
  font-size: 30rpx;
  color: $uni-text-color;
}

.send-btn {
  width: 72rpx;
  height: 72rpx;
  background: $uni-color-primary;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  
  &.disabled {
    background: $uni-text-color-disable;
    opacity: 0.5;
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
</style>

