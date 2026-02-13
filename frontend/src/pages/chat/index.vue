<template>
  <view class="chat-page">
    <!-- Message area -->
    <scroll-view
      scroll-y
      class="message-list"
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view v-if="chatStore.messages.length === 0" class="empty-hint">
        <text class="empty-text">你好！我是BetaStay智能定价助手。</text>
        <text class="empty-text">可以问我关于房源管理和定价的问题。</text>
      </view>
      <ChatBubble
        v-for="(msg, idx) in chatStore.messages"
        :key="idx"
        :message="msg"
      />
      <view v-if="chatStore.loading" class="loading-hint">
        <text>AI正在思考中...</text>
      </view>
    </scroll-view>

    <!-- Input area -->
    <view class="input-area">
      <input
        v-model="inputText"
        class="msg-input"
        placeholder="输入消息..."
        confirm-type="send"
        @confirm="handleSend"
        :disabled="chatStore.loading"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || chatStore.loading"
        @click="handleSend"
      >
        发送
      </button>
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
import { ref, nextTick } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'
import ConfirmPanel from '../../components/ConfirmPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTop = ref(0)
const showConfirm = ref(false)
const confirmData = ref<Record<string, any>>({})

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  inputText.value = ''
  await chatStore.sendMessage(text)
  await nextTick()
  scrollTop.value = 99999
}

function handleConfirm() {
  showConfirm.value = false
  // TODO: call confirm API
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}
.message-list {
  flex: 1;
  padding: 20rpx;
  display: flex;
  flex-direction: column;
}
.empty-hint {
  text-align: center;
  padding: 120rpx 40rpx;
}
.empty-text {
  display: block;
  color: #999;
  font-size: 28rpx;
  margin-bottom: 12rpx;
}
.loading-hint {
  text-align: center;
  padding: 20rpx;
  color: #999;
  font-size: 24rpx;
}
.input-area {
  display: flex;
  align-items: center;
  padding: 16rpx 20rpx;
  background: #fff;
  border-top: 1rpx solid #eee;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
}
.msg-input {
  flex: 1;
  height: 72rpx;
  background: #f5f5f5;
  border-radius: 36rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
}
.send-btn {
  margin-left: 16rpx;
  background: #07c160;
  color: #fff;
  font-size: 28rpx;
  padding: 0 32rpx;
  height: 72rpx;
  line-height: 72rpx;
  border-radius: 36rpx;
}
</style>
