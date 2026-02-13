import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat'

export interface ChatMessage {
  id?: number
  role: string
  content: string
  thinking?: string
  created_at: string
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<any[]>([])
  const currentConversationId = ref<number | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const thinking = ref(false)
  const error = ref<string | null>(null)

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
        const conv = await chatApi.createConversation('新对话')
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
            onDone: (data) => {
              thinking.value = false
              loading.value = false
              const msg = messages.value[assistantIdx]
              if (msg) {
                msg.id = data.id
                msg.content = data.content
                msg.thinking = data.thinking
                msg.created_at = data.created_at
              }
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

  async function loadMessages(conversationId: number) {
    currentConversationId.value = conversationId
    messages.value = await chatApi.getMessages(conversationId)
  }

  return { conversations, currentConversationId, messages, loading, thinking, error, createConversation, sendMessage, loadMessages }
})
