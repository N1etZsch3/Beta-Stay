import { request } from './request'

export function createConversation(title?: string) {
  return request({ url: '/chat/conversations', method: 'POST', data: { title } })
}

export function listConversations() {
  return request({ url: '/chat/conversations' })
}

export function sendMessage(conversationId: number, content: string) {
  return request({
    url: `/chat/conversations/${conversationId}/messages`,
    method: 'POST',
    data: { content },
  })
}

export function getMessages(conversationId: number) {
  return request({ url: `/chat/conversations/${conversationId}/messages` })
}
