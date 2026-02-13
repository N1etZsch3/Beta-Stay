import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat'

export interface ChatMessage {
  id?: number
  role: string
  content: string
  thinking?: string
  created_at: string
  // 消息附带的结构化数据
  pricing?: {
    pricing_record_id: number
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<any[]>([])
  const currentConversationId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const thinking = ref(false)
  const error = ref<string | null>(null)

  const pendingAction = ref<{
    action_id: string
    action_type: string
    display: { title: string; items: Record<string, string> }
    data: Record<string, any>
  } | null>(null)

  const pricingResult = ref<{
    pricing_record_id: number
    property_id: number
    target_date: string
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  } | null>(null)

  async function createConversation(title?: string) {
    const conv = await chatApi.createConversation(title)
    conversations.value.unshift(conv)
    currentConversationId.value = conv.id
    messages.value = []
    return conv
  }

  async function sendMessage(content: string) {
    error.value = null

    // Push user message immediately
    messages.value.push({ role: 'user', content, created_at: new Date().toISOString() })
    loading.value = true
    thinking.value = true

    try {
      // Create conversation if needed
      if (!currentConversationId.value) {
        const conv = await chatApi.createConversation()
        conversations.value.unshift(conv)
        currentConversationId.value = conv.id
      }

      // Add a placeholder assistant message for streaming
      const assistantIdx = messages.value.length
      messages.value.push({
        role: 'assistant',
        content: '',
        thinking: '',
        created_at: new Date().toISOString(),
      })

      return new Promise<void>((resolve, reject) => {
        chatApi.sendMessageStream(
          currentConversationId.value!,
          content,
          {
            onThinking: (chunk) => {
              thinking.value = true
              const msg = messages.value[assistantIdx]
              if (msg) msg.thinking = (msg.thinking || '') + chunk
            },
            onContent: (chunk) => {
              thinking.value = false
              const msg = messages.value[assistantIdx]
              if (msg) msg.content += chunk
            },
            onAction: (data) => {
              pendingAction.value = data
            },
            onPricing: (data) => {
              pricingResult.value = data
            },
            onDone: (data) => {
              thinking.value = false
              loading.value = false
              const msg = messages.value[assistantIdx]
              if (msg) {
                msg.id = data.id
                msg.content = data.content
                msg.thinking = data.thinking
                msg.created_at = data.created_at
                // 如果有定价结果，附加到消息上
                if (pricingResult.value) {
                  msg.pricing = {
                    pricing_record_id: pricingResult.value.pricing_record_id,
                    conservative_price: pricingResult.value.conservative_price,
                    suggested_price: pricingResult.value.suggested_price,
                    aggressive_price: pricingResult.value.aggressive_price,
                  }
                  pricingResult.value = null
                }
              }
              // 刷新会话列表以获取后端自动设置的标题
              loadConversations()
              resolve()
            },
            onError: (err) => {
              thinking.value = false
              loading.value = false
              const msg = messages.value[assistantIdx]
              if (msg) msg.content = `发送失败：${err.message}`
              error.value = err.message
              reject(err)
            },
          },
        )
      })
    } catch (e: any) {
      thinking.value = false
      loading.value = false
      error.value = e?.message || '发送失败，请重试'
      throw e
    }
  }

  async function loadMessages(conversationId: string) {
    currentConversationId.value = conversationId
    messages.value = await chatApi.getMessages(conversationId)
  }

  async function loadConversations() {
    conversations.value = await chatApi.listConversations()
  }

  async function switchConversation(conversationId: string) {
    currentConversationId.value = conversationId
    pendingAction.value = null
    pricingResult.value = null
    await loadMessages(conversationId)
  }

  async function newConversation() {
    currentConversationId.value = null
    messages.value = []
    pendingAction.value = null
    pricingResult.value = null
  }

  async function confirmPendingAction() {
    if (!pendingAction.value || !currentConversationId.value) return
    const result = await chatApi.confirmAction(
      currentConversationId.value,
      pendingAction.value.action_id,
    )
    pendingAction.value = null
    // 追加确认成功消息
    if (result && result.success) {
      const confirmMsg = result.type === 'property'
        ? `房源「${result.name}」已成功录入`
        : `反馈已记录`
      messages.value.push({
        role: 'assistant',
        content: confirmMsg,
        created_at: new Date().toISOString(),
      })
    }
    return result
  }

  function cancelPendingAction() {
    pendingAction.value = null
  }

  async function deleteConversation(conversationId: string) {
    await chatApi.deleteConversation(conversationId)
    conversations.value = conversations.value.filter(c => c.id !== conversationId)
    // 如果删除的是当前会话，重置状态
    if (currentConversationId.value === conversationId) {
      currentConversationId.value = null
      messages.value = []
      pendingAction.value = null
      pricingResult.value = null
    }
  }

  return {
    conversations, currentConversationId, messages, loading, thinking, error,
    pendingAction, pricingResult,
    createConversation, sendMessage, loadMessages,
    loadConversations, switchConversation, newConversation,
    confirmPendingAction, cancelPendingAction, deleteConversation,
  }
})
