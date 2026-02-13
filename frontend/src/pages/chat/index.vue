<template>
  <view class="chat-page">
    <!-- Header -->
    <view class="chat-header">
      <view class="header-left" @click="showDrawer = !showDrawer">
        <text class="menu-icon">☰</text>
      </view>
      <text class="header-title">{{ currentTitle }}</text>
      <view class="header-right" @click="handleNewChat">
        <text class="new-icon">+</text>
      </view>
    </view>

    <!-- Conversation drawer -->
    <view v-if="showDrawer" class="drawer-mask" @click="showDrawer = false">
      <view class="drawer-panel" @click.stop>
        <view class="drawer-title">历史会话</view>
        <scroll-view scroll-y class="drawer-list">
          <view
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            :class="['drawer-item', { active: conv.id === chatStore.currentConversationId }]"
            @click="handleSwitchConv(conv.id)"
          >
            <text class="drawer-item-title">{{ conv.title || '新对话' }}</text>
          </view>
          <view v-if="chatStore.conversations.length === 0" class="drawer-empty">
            <text>暂无历史会话</text>
          </view>
        </scroll-view>
      </view>
    </view>

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
        <template v-for="(msg, idx) in chatStore.messages" :key="idx">
          <ChatBubble
            :message="msg"
            :is-streaming="idx === chatStore.messages.length - 1 && chatStore.loading"
          />
          <!-- 定价卡片（跟在助手消息后面） -->
          <PriceCard
            v-if="msg.role === 'assistant' && msg.pricing"
            :pricing="msg.pricing"
            @adopt="handleAdopt(msg.pricing!.pricing_record_id, $event)"
            @reject="handleReject(msg.pricing!.pricing_record_id)"
            @adjust="handleAdjust(msg.pricing!.pricing_record_id)"
          />
        </template>

        <!-- Loading / Thinking Indicator (Implicit in last message now, but keep fallback) -->
        <view v-if="chatStore.loading && chatStore.messages.length === 0" class="status-tip">
           <text>AI正在准备...</text>
        </view>

        <!-- Bottom Spacer -->
        <view class="scroll-bottom-spacer" />
      </view>
    </scroll-view>

    <!-- Confirm panel -->
    <ConfirmPanel
      :visible="!!chatStore.pendingAction"
      :data="chatStore.pendingAction?.display?.items || {}"
      @confirm="handleConfirmAction"
      @cancel="chatStore.cancelPendingAction()"
    />

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
import { ref, nextTick, watch, onMounted, computed } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'
import PriceCard from '../../components/PriceCard.vue'
import ConfirmPanel from '../../components/ConfirmPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTop = ref(0)
const showDrawer = ref(false)

const currentTitle = computed(() => {
  if (!chatStore.currentConversationId) return '新对话'
  const conv = chatStore.conversations.find((c: any) => c.id === chatStore.currentConversationId)
  return conv?.title || '对话'
})

onMounted(() => {
  chatStore.loadConversations()
})

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

// --- PriceCard handlers ---
async function handleAdopt(pricingRecordId: number, price: number) {
  inputText.value = `我采纳建议价 ¥${price}（定价记录ID: ${pricingRecordId}）`
  await handleSend()
}

function handleReject(pricingRecordId: number) {
  inputText.value = `这个定价不太合适（定价记录ID: ${pricingRecordId}）`
  handleSend()
}

function handleAdjust(pricingRecordId: number) {
  inputText.value = `我想手动调整价格（定价记录ID: ${pricingRecordId}），调整为 `
  // 留给用户输入价格
}

// --- ConfirmPanel handler ---
async function handleConfirmAction() {
  try {
    await chatStore.confirmPendingAction()
    scrollToBottom()
  } catch {
    // 确认失败，保持弹窗
  }
}

// --- Conversation drawer handlers ---
function handleNewChat() {
  chatStore.newConversation()
  showDrawer.value = false
}

async function handleSwitchConv(convId: string) {
  await chatStore.switchConversation(convId)
  showDrawer.value = false
  await nextTick()
  scrollToBottom()
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

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  height: 88rpx;
  background: #fff;
  border-bottom: 1rpx solid $uni-border-color;
  flex-shrink: 0;
}

.header-left, .header-right {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-icon, .new-icon {
  font-size: 40rpx;
  color: $uni-text-color;
}

.header-title {
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-color-title;
}

.drawer-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  z-index: 998;
}

.drawer-panel {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 70%;
  max-width: 600rpx;
  background: #fff;
  padding: 40rpx 0;
  box-shadow: 4rpx 0 16rpx rgba(0,0,0,0.1);
}

.drawer-title {
  font-size: 32rpx;
  font-weight: 700;
  padding: 0 32rpx 24rpx;
  border-bottom: 1rpx solid $uni-border-color;
  color: $uni-color-title;
}

.drawer-list {
  height: calc(100% - 80rpx);
}

.drawer-item {
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid #f5f5f5;
  transition: background 0.2s;

  &.active {
    background: rgba($uni-color-primary, 0.08);
  }

  &:active {
    background: $uni-bg-color-hover;
  }
}

.drawer-item-title {
  font-size: 28rpx;
  color: $uni-text-color;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-empty {
  padding: 60rpx 32rpx;
  text-align: center;
  color: $uni-text-color-placeholder;
  font-size: 26rpx;
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
