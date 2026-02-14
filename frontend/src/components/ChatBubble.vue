<template>
  <view :class="['chat-bubble-wrapper', message.role === 'user' ? 'wrapper-right' : 'wrapper-left']">
    <!-- AI Icon -->
    <view v-if="message.role === 'assistant'" class="ai-avatar">
      <text class="sparkle-icon">✨</text>
    </view>

    <view class="bubble-content-stack">
      <!-- User Message Bubble -->
      <view
        v-if="message.role === 'user'"
        class="user-bubble"
        @longpress.prevent="onLongPress"
      >
        <!-- Normal display -->
        <text v-if="!isEditing" class="bubble-text">{{ message.content }}</text>
        <!-- Inline editor -->
        <view v-else class="edit-area">
          <textarea
            v-model="editText"
            class="edit-textarea"
            :auto-height="true"
            :maxlength="-1"
            placeholder="编辑消息..."
          />
          <view class="edit-actions">
            <view class="edit-btn cancel-btn" @click="cancelEdit">
              <text>取消</text>
            </view>
            <view class="edit-btn submit-btn" @click="submitEdit">
              <text>提交</text>
            </view>
          </view>
        </view>
      </view>

      <!-- AI Message Content -->
      <view
        v-else
        class="ai-content"
        @longpress.prevent="onLongPress"
      >
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

        <!-- Markdown rendered content -->
        <view class="md-body" v-html="renderedHtml"></view>

        <!-- Blinking Cursor -->
        <view v-if="isStreaming" class="cursor-blink"></view>
      </view>
    </view>

    <!-- Long-press Action Modal Overlay -->
    <view v-if="showActions" class="action-overlay" @click="closeActions">
      <view
        ref="modalRef"
        class="action-modal"
        :style="modalStyle"
        @click.stop
      >
        <view class="action-row" @click="handleAction('copy')">
          <view class="action-icon-wrap">
            <text class="action-icon">📋</text>
          </view>
          <text class="action-text">复制</text>
        </view>
        <view v-if="message.role === 'user'" class="action-row" @click="handleAction('edit')">
          <view class="action-icon-wrap">
            <text class="action-icon">✏️</text>
          </view>
          <text class="action-text">编辑</text>
        </view>
        <view v-if="message.role === 'assistant'" class="action-row" @click="handleAction('regenerate')">
          <view class="action-icon-wrap">
            <text class="action-icon">🔄</text>
          </view>
          <text class="action-text">重新生成</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  message: {
    id?: number
    role: string
    content: string
    thinking?: string
    created_at: string
  }
  isStreaming?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', messageId: number, newContent: string): void
  (e: 'regenerate', messageId: number): void
}>()

const showThinking = ref(false)
const showActions = ref(false)
const isEditing = ref(false)
const editText = ref('')
const modalRef = ref<any>(null)
const modalPos = ref({ x: 0, y: 0 })

// Estimated modal dimensions for initial clamping (refined after render)
const MODAL_W = 180
const MODAL_H_USER = 120  // 2 rows: copy + edit
const MODAL_H_AI = 120    // 2 rows: copy + regenerate
const EDGE_PAD = 16

const modalStyle = computed(() => ({
  position: 'fixed' as const,
  left: `${modalPos.value.x}px`,
  top: `${modalPos.value.y}px`,
}))

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

const renderedHtml = computed(() => {
  if (props.message.role === 'user') return ''
  const content = props.message.content || ''
  if (!content) return ''

  try {
    return marked.parse(content) as string
  } catch {
    return content
  }
})

// --- Long Press & Actions ---
function onLongPress(e: any) {
  if (props.isStreaming || !props.message.content) return

  // Disable scroll on parent page to prevent conflict
  // #ifdef H5
  document.body.style.overflow = 'hidden'
  // #endif

  // Get touch point
  const touch = e.touches?.[0] || e.changedTouches?.[0]
  const cx = touch?.clientX ?? e.detail?.x ?? 0
  const cy = touch?.clientY ?? e.detail?.y ?? 0

  // Viewport dimensions
  const vw = window.innerWidth || uni.getSystemInfoSync().windowWidth
  const vh = window.innerHeight || uni.getSystemInfoSync().windowHeight

  // Estimate modal height based on role
  const estH = props.message.role === 'user' ? MODAL_H_USER : MODAL_H_AI

  // Clamp so modal stays within viewport
  let x = cx - MODAL_W / 2
  let y = cy - estH - 12  // prefer above touch point

  // If not enough space above, show below
  if (y < EDGE_PAD) {
    y = cy + 12
  }
  // If below would overflow, push up
  if (y + estH > vh - EDGE_PAD) {
    y = vh - EDGE_PAD - estH
  }
  // Clamp horizontal
  x = Math.max(EDGE_PAD, Math.min(x, vw - MODAL_W - EDGE_PAD))
  y = Math.max(EDGE_PAD, y)

  modalPos.value = { x, y }
  showActions.value = true

  // Refine position after actual DOM render
  nextTick(() => {
    const el = modalRef.value?.$el || modalRef.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    let fx = modalPos.value.x
    let fy = modalPos.value.y
    // Clamp with actual size
    if (fx + rect.width > vw - EDGE_PAD) fx = vw - EDGE_PAD - rect.width
    if (fy + rect.height > vh - EDGE_PAD) fy = vh - EDGE_PAD - rect.height
    fx = Math.max(EDGE_PAD, fx)
    fy = Math.max(EDGE_PAD, fy)
    modalPos.value = { x: fx, y: fy }
  })
}

function closeActions() {
  showActions.value = false
  // #ifdef H5
  document.body.style.overflow = ''
  // #endif
}

function handleAction(action: string) {
  closeActions()
  switch (action) {
    case 'copy':
      handleCopy()
      break
    case 'edit':
      startEdit()
      break
    case 'regenerate':
      if (props.message.id) {
        emit('regenerate', props.message.id)
      }
      break
  }
}

// --- Copy ---
function handleCopy() {
  const text = props.message.content || ''
  // #ifdef H5
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(showCopied).catch(() => {
      fallbackCopy(text)
    })
  } else {
    fallbackCopy(text)
  }
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: text,
    showToast: false,
    success: () => showCopied(),
  })
  // #endif
}

function fallbackCopy(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
  showCopied()
}

function showCopied() {
  uni.showToast({ title: '已复制', icon: 'none' })
}

// --- Edit ---
function startEdit() {
  editText.value = props.message.content
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editText.value = ''
}

function submitEdit() {
  const newContent = editText.value.trim()
  if (!newContent || !props.message.id) return
  isEditing.value = false
  emit('edit', props.message.id, newContent)
}
</script>

<style scoped lang="scss">
.chat-bubble-wrapper {
  display: flex;
  margin-bottom: 40rpx;
  width: 100%;
  position: relative;
  box-sizing: border-box;
}

.wrapper-left {
  flex-direction: column; /* Avatar above content */
  align-items: flex-start;
  padding: 0 48rpx; /* Equal spacing from edges */
  gap: 16rpx;
}

.wrapper-right {
  justify-content: flex-end;
}

/* Avatar */
.ai-avatar {
  width: 64rpx;
  height: 64rpx;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 0;
  box-shadow: none;
  background: transparent;
  align-self: flex-start;
}

.sparkle-icon {
  font-size: 40rpx;
}

.bubble-content-stack {
  max-width: 100%; /* Fill available width (controlled by wrapper padding) */
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 0;
}

/* User Bubble */
.user-bubble {
  background: linear-gradient(135deg, $uni-color-primary, lighten($uni-color-primary, 10%));
  color: #fff;
  padding: 24rpx 32rpx;
  border-radius: 36rpx;
  border-top-right-radius: 4rpx;
  box-shadow: 0 4rpx 12rpx rgba(26, 75, 156, 0.15);
  font-size: 30rpx;
  line-height: 1.5;
  max-width: 80%;
  margin-left: auto;
}

/* AI Content - Clean Style (Gemini/ChatGPT like) */
.ai-content {
  background: transparent;
  color: $uni-color-title;
  padding: 0;
  border-radius: 0;
  box-shadow: none;
  font-size: 30rpx;
  line-height: 1.6;
  margin-top: 2rpx;
}

/* ===== Modal Overlay ===== */
.action-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  background: rgba(0, 0, 0, 0.35);
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.action-modal {
  background: rgba(30, 41, 59, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 28rpx;
  padding: 12rpx 0;
  min-width: 320rpx;
  box-shadow:
    0 16rpx 48rpx rgba(0, 0, 0, 0.3),
    0 0 0 1rpx rgba(255, 255, 255, 0.08) inset;
  animation: modalPop 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modalPop {
  from {
    opacity: 0;
    transform: scale(0.85);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.action-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx 36rpx;
  transition: background 0.15s;

  &:active {
    background: rgba(255, 255, 255, 0.08);
  }

  &:first-child {
    border-radius: 28rpx 28rpx 0 0;
  }

  &:last-child {
    border-radius: 0 0 28rpx 28rpx;
  }

  &:not(:last-child) {
    border-bottom: 1rpx solid rgba(255, 255, 255, 0.06);
  }
}

.action-icon-wrap {
  width: 56rpx;
  height: 56rpx;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-icon {
  font-size: 32rpx;
}

.action-text {
  font-size: 30rpx;
  color: #E2E8F0;
  font-weight: 500;
}

/* ===== Markdown Body Styles ===== */
.md-body {
  word-break: break-word;
  overflow-wrap: break-word;

  :deep(p) {
    margin: 8rpx 0;
    line-height: 1.7;
    color: $uni-color-title;
  }

  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin: 24rpx 0 16rpx;
    font-weight: 700;
    line-height: 1.4;
    color: $uni-color-title;
  }

  :deep(h1) { font-size: 40rpx; border-bottom: 2rpx solid #F1F5F9; padding-bottom: 8rpx; }
  :deep(h2) { font-size: 36rpx; }
  :deep(h3) { font-size: 34rpx; }
  :deep(h4) { font-size: 32rpx; }

  :deep(strong) {
    font-weight: 700;
    color: $uni-color-title;
  }

  :deep(em) {
    font-style: italic;
  }

  :deep(ul), :deep(ol) {
    padding-left: 36rpx;
    margin: 12rpx 0;
  }

  :deep(li) {
    margin: 8rpx 0;
    line-height: 1.6;
  }

  :deep(blockquote) {
    border-left: 8rpx solid $uni-color-primary;
    padding: 16rpx 24rpx;
    margin: 24rpx 0;
    background: #F8FAFC;
    border-radius: 0 12rpx 12rpx 0;
    color: $uni-text-color-grey;
  }

  :deep(a) {
    color: $uni-color-primary;
    text-decoration: none;
    font-weight: 500;
    border-bottom: 1rpx solid rgba($uni-color-primary, 0.3);
  }

  :deep(hr) {
    border: none;
    border-top: 2rpx dashed #E2E8F0;
    margin: 32rpx 0;
  }

  /* Inline code */
  :deep(code) {
    background: #F1F5F9;
    padding: 4rpx 12rpx;
    border-radius: 8rpx;
    font-family: 'Courier New', Courier, monospace;
    font-size: 26rpx;
    color: #0F172A;
    border: 1rpx solid #E2E8F0;
  }

  /* Code blocks */
  :deep(pre) {
    margin: 20rpx 0;
    background: #1E293B; /* Keep dark bg for code blocks for better syntax highlighting contrast */
    border-radius: 16rpx;
    overflow: hidden;
    position: relative;
    box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.1);

    code {
      display: block;
      padding: 24rpx;
      color: #E2E8F0;
      font-family: 'Courier New', Courier, monospace;
      font-size: 26rpx;
      white-space: pre;
      overflow-x: auto;
      background: transparent;
      border: none;
      border-radius: 0;
    }
  }

  /* Tables */
  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 24rpx 0;
    font-size: 26rpx;
    overflow-x: auto;
    display: block;
    border-radius: 12rpx;
    border-style: hidden; /* Hide outer border to use box-shadow */
    box-shadow: 0 0 0 1rpx #E2E8F0;
  }

  :deep(th), :deep(td) {
    border: 1rpx solid #E2E8F0;
    padding: 16rpx 20rpx;
    text-align: left;
  }

  :deep(th) {
    background: #F8FAFC;
    font-weight: 600;
    color: $uni-color-title;
  }

  :deep(tr:nth-child(even)) {
    background: #F8FAFC;
  }
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

/* Inline Editor */
.edit-area {
  width: 100%;
}

.edit-textarea {
  width: 100%;
  min-height: 80rpx;
  padding: 16rpx;
  font-size: 30rpx;
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.2);
  line-height: 1.5;
  box-sizing: border-box;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16rpx;
  margin-top: 12rpx;
}

.edit-btn {
  padding: 8rpx 24rpx;
  border-radius: 12rpx;
  font-size: 26rpx;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #CBD5E1;
}

.submit-btn {
  background: $uni-color-primary;
  color: #fff;
}
</style>
