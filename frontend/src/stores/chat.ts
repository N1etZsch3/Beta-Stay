import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<any[]>([])
  const currentConversationId = ref<number | null>(null)
  const messages = ref<any[]>([])
  const loading = ref(false)

  async function createConversation(title?: string) {
    const conv = await chatApi.createConversation(title)
    conversations.value.unshift(conv)
    currentConversationId.value = conv.id
    messages.value = []
    return conv
  }

  async function sendMessage(content: string) {
    if (!currentConversationId.value) {
      await createConversation('新对话')
    }
    messages.value.push({ role: 'user', content, created_at: new Date().toISOString() })
    loading.value = true
    try {
      const reply = await chatApi.sendMessage(currentConversationId.value!, content)
      messages.value.push(reply)
      return reply
    } finally {
      loading.value = false
    }
  }

  async function loadMessages(conversationId: number) {
    currentConversationId.value = conversationId
    messages.value = await chatApi.getMessages(conversationId)
  }

  return { conversations, currentConversationId, messages, loading, createConversation, sendMessage, loadMessages }
})
