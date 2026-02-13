<template>
  <view class="chat-page">
    <!-- Custom Header -->
    <view class="custom-header">
      <view class="status-bar-placeholder"></view>
      <view class="header-content">
        <view class="header-left" @click="toggleSidebar">
          <text class="header-icon">≡</text>
        </view>
        <text class="header-title">智能助手</text>
        <view class="header-right" @click="handleNewChat">
          <text class="header-icon">＋</text>
        </view>
      </view>
    </view>

    <!-- Sidebar (Drawer) -->
    <view class="sidebar-mask" :class="{ show: showSidebar }" @click="toggleSidebar"></view>
    <view class="sidebar-drawer" :class="{ show: showSidebar }">
      <view class="sidebar-header">
        <text class="sidebar-title">历史会话</text>
      </view>
      <scroll-view scroll-y class="sidebar-content">
        <view 
          v-for="conv in chatStore.conversations" 
          :key="conv.id"
          class="sidebar-item"
          :class="{ active: conv.id === chatStore.currentConversationId }"
          @click="switchChat(conv.id)"
        >
          <view class="item-icon-wrapper">
             <text class="item-icon">💬</text>
          </view>
          <view class="item-info">
             <text class="conv-title">{{ conv.title || '新对话' }}</text>
             <text class="conv-date">{{ formatDate(conv.last_active_at) }}</text>
          </view>
          <view class="delete-btn" @click.stop="handleDeleteChat(conv.id)">
            <text class="delete-icon">🗑️</text>
          </view>
        </view>
        
        <view v-if="chatStore.conversations.length === 0" class="empty-history">
          <text>暂无历史会话</text>
        </view>
      </scroll-view>
      
      <view class="sidebar-footer">
        <view class="user-profile">
          <view class="avatar">U</view>
          <text class="username">BetaStay User</text>
        </view>
      </view>
    </view>

    <!-- Message area (Flex Item: Grow) -->
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
          <PriceCard
            v-if="msg.role === 'assistant' && msg.pricing"
            :pricing="msg.pricing"
            @adopt="handleAdopt(msg.pricing!.pricing_record_id, $event)"
            @reject="handleReject(msg.pricing!.pricing_record_id)"
            @adjust="handleAdjust(msg.pricing!.pricing_record_id)"
          />
        </template>

        <!-- Loading / Thinking Indicator -->
        <view v-if="chatStore.loading && chatStore.messages.length === 0" class="status-tip">
           <text>AI正在准备...</text>
        </view>
      </view>
    </scroll-view>

    <!-- Input Section (Static Flex Item) -->
    <view class="input-section">
      <view class="input-card">
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
           <view 
             :class="['send-btn', { disabled: !inputText.trim() || chatStore.loading }]"
             @click="handleSend"
           >
            <text class="send-icon">↑</text>
           </view>
        </view>
      </view>
    </view>
    
    <!-- Confirm panel (Fixed Overlay) -->
    <ConfirmPanel
      :visible="!!chatStore.pendingAction"
      :data="chatStore.pendingAction?.display?.items || {}"
      @confirm="handleConfirmAction"
      @cancel="chatStore.cancelPendingAction()"
    />
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'
import PriceCard from '../../components/PriceCard.vue'
import ConfirmPanel from '../../components/ConfirmPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTop = ref(0)
const showSidebar = ref(false)

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
  scrollTop.value = scrollTop.value + 1
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  inputText.value = ''
  // 立即滚动到底部，让用户消息可见
  await nextTick()
  scrollToBottom()
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

// --- Toggle Sidebar ---
function toggleSidebar() {
  showSidebar.value = !showSidebar.value
}

// --- Chat Management ---
async function handleNewChat() {
  await chatStore.newConversation()
  showSidebar.value = false
}

async function switchChat(id: string) {
  if (id === chatStore.currentConversationId) {
    showSidebar.value = false
    return
  }
  await chatStore.switchConversation(id)
  showSidebar.value = false
}

async function handleDeleteChat(id: string) {
  uni.showModal({
    title: '确认删除',
    content: '删除后无法恢复，确认删除该会话？',
    success: async (res) => {
      if (res.confirm) {
        await chatStore.deleteConversation(id)
      }
    },
  })
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

function formatDate(isoStr: string) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped lang="scss">
.chat-page {
  background-color: $uni-bg-color-grey;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* Custom Header */
.custom-header {
  background-color: #1a1a1a; 
  color: #fff;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  flex-shrink: 0;
}

.status-bar-placeholder {
  height: var(--status-bar-height);
  width: 100%;
}

.header-content {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
}

.header-title {
  font-size: 16px; 
  font-weight: 600;
  color: #fff;
}

.header-left, .header-right {
  width: 40px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:active {
    opacity: 0.7;
  }
}

.header-icon {
  font-size: 24px; 
  font-weight: 300;
  color: #fff;
}

/* Sidebar */
.sidebar-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  z-index: 900;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
  
  &.show {
    opacity: 1;
    pointer-events: auto;
  }
}

.sidebar-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px; 
  max-width: 80%;
  background: #1c1c1e; 
  z-index: 901;
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0,0,0,0.3);
  
  &.show {
    transform: translateX(0);
  }
}

.sidebar-header {
  height: calc(56px + var(--status-bar-height)); 
  padding-top: var(--status-bar-height);
  padding-left: 24px;
  display: flex;
  align-items: center;
}

.sidebar-title {
  color: #fff;
  font-size: 24px; 
  font-weight: 700;
  letter-spacing: 0.5px;
}

.sidebar-content {
  flex: 1;
  height: 0;
  padding: 12px 16px;
  box-sizing: border-box;
  overflow: hidden;
}

/* Sidebar Item - Hover/Active Only */
.sidebar-item {
  padding: 12px 10px 12px 16px;
  margin-bottom: 4px; 
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: transparent; 
  transition: all 0.2s;
  
  &:active {
    background: rgba(255, 255, 255, 0.08);
  }
  
  &.active {
    background: transparent; 
    
    .conv-title {
      color: $uni-color-primary;
      font-weight: 600;
    }
    
    .item-icon-wrapper {
        background: $uni-color-primary;
    }
    
    .item-icon {
        color: #fff;
    }
  }
}

.item-icon-wrapper {
  width: 40px; 
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.1);
  transition: background 0.2s;
}

.item-icon {
  font-size: 20px;
  color: #8e8e93;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.conv-title {
  font-size: 16px;
  color: #e5e5e7;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-date {
  font-size: 12px;
  color: #8e8e93;
}

.delete-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.4;
  transition: all 0.2s;
  flex-shrink: 0;
  
  &:active {
    opacity: 1;
    background: rgba(255, 59, 48, 0.15);
  }
}

.delete-icon {
  font-size: 16px;
}

.empty-history {
  padding: 40px;
  text-align: center;
  color: #636366;
  font-size: 14px;
}

/* Footer with TabBar clearance */
.sidebar-footer {
  padding: 24px;
  /* Add padding for TabBar + Safe Area */
  padding-bottom: calc(50px + 24px + constant(safe-area-inset-bottom));
  padding-bottom: calc(50px + 24px + env(safe-area-inset-bottom));
  background: rgba(28, 28, 30, 0.9);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
}

.username {
  color: #fff;
  font-size: 16px;
  font-weight: 500;
}

/* Chat Area - Flex Item */
.message-list {
  flex: 1;
  height: 0; 
  width: 100%;
}

.list-padding {
  padding: 32rpx 24rpx;
  padding-bottom: 20rpx; /* Minimal padding */
}

/* Empty State */
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
  color: #1E293B; 
  margin-bottom: 16rpx;
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

/* Input Section - Static Flex Item */
.input-section {
  flex-shrink: 0;
  background: linear-gradient(to top, rgba(248,250,252, 1) 90%, rgba(248,250,252, 0) 100%);
  padding: 24rpx 32rpx;
  
  /* Robust positioning above TabBar */
  padding-bottom: calc(24rpx + var(--window-bottom) + constant(safe-area-inset-bottom));
  padding-bottom: calc(24rpx + var(--window-bottom) + env(safe-area-inset-bottom));
  
  z-index: 50;
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
  border-radius: 36rpx;
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
