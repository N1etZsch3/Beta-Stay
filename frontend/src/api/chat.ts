import { request, getBaseUrl } from './request'

export function createConversation(title?: string) {
  return request({ url: '/chat/conversations', method: 'POST', data: { title } })
}

export function listConversations() {
  return request({ url: '/chat/conversations' })
}

export function sendMessage(conversationId: string, content: string) {
  return request({
    url: `/chat/conversations/${conversationId}/messages`,
    method: 'POST',
    data: { content },
    timeout: 120000,
  })
}

export function getMessages(conversationId: string) {
  return request({ url: `/chat/conversations/${conversationId}/messages` })
}

export function confirmAction(conversationId: string, actionId: string) {
  return request({
    url: `/chat/conversations/${conversationId}/confirm`,
    method: 'POST',
    data: { action_id: actionId },
  })
}

export function deleteConversation(conversationId: string) {
  return request({
    url: `/chat/conversations/${conversationId}`,
    method: 'DELETE',
  })
}

export interface StreamCallbacks {
  onThinking?: (chunk: string) => void
  onContent?: (chunk: string) => void
  onAction?: (data: {
    action_id: string
    action_type: string
    display: { title: string; items: Record<string, string> }
    data: Record<string, any>
  }) => void
  onPricing?: (data: {
    pricing_record_id: number
    property_id: number
    target_date: string
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }) => void
  onForm?: (data: {
    form_type: string
    fields: Array<{
      key: string
      label: string
      type: string
      required: boolean
      placeholder?: string
      options?: string[]
    }>
  }) => void
  onDone?: (data: {
    id: number
    content: string
    thinking: string
    created_at: string
    pending_actions: any[]
  }) => void
  onError?: (error: Error) => void
  onAbort?: () => void
}

/**
 * 公共 SSE 解析函数 — 从 Response 的 ReadableStream 中解析 SSE 事件并分发回调
 */
async function parseSSEStream(response: Response, callbacks: StreamCallbacks) {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE events from buffer
    const lines = buffer.split('\n')
    buffer = ''

    let currentEvent = ''
    let currentData = ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6)
      } else if (line === '' && currentEvent && currentData) {
        // Empty line = end of event
        try {
          const parsed = JSON.parse(currentData)
          if (currentEvent === 'thinking' && callbacks.onThinking) {
            callbacks.onThinking(parsed.content)
          } else if (currentEvent === 'content' && callbacks.onContent) {
            callbacks.onContent(parsed.content)
          } else if (currentEvent === 'action' && callbacks.onAction) {
            callbacks.onAction(parsed)
          } else if (currentEvent === 'pricing' && callbacks.onPricing) {
            callbacks.onPricing(parsed)
          } else if (currentEvent === 'form' && callbacks.onForm) {
            callbacks.onForm(parsed)
          } else if (currentEvent === 'done' && callbacks.onDone) {
            callbacks.onDone(parsed)
          }
        } catch {
          // Ignore parse errors for incomplete chunks
        }
        currentEvent = ''
        currentData = ''
      } else if (line !== '') {
        // Incomplete event, put back in buffer
        buffer = line + '\n'
      }
    }
  }
}

/**
 * 通用 SSE fetch 封装 — 发起请求 + 解析流 + 错误处理
 */
function fetchSSEStream(
  url: string,
  body: Record<string, any>,
  callbacks: StreamCallbacks,
): AbortController {
  const controller = new AbortController()
  const baseUrl = getBaseUrl()

  fetch(`${baseUrl}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status}`)
      }
      await parseSSEStream(response, callbacks)
    })
    .catch((err) => {
      if (err.name === 'AbortError') {
        callbacks.onAbort?.()
      } else {
        callbacks.onError?.(err)
      }
    })

  return controller
}

/**
 * 流式发送消息 (SSE)
 */
export function sendMessageStream(
  conversationId: string,
  content: string,
  callbacks: StreamCallbacks,
): AbortController {
  return fetchSSEStream(
    `/chat/conversations/${conversationId}/messages/stream`,
    { content },
    callbacks,
  )
}

/**
 * 编辑消息后重新发送 (SSE)
 */
export function editMessageStream(
  conversationId: string,
  messageId: number,
  content: string,
  callbacks: StreamCallbacks,
): AbortController {
  return fetchSSEStream(
    `/chat/conversations/${conversationId}/messages/edit`,
    { message_id: messageId, content },
    callbacks,
  )
}

/**
 * 重新生成 AI 回复 (SSE)
 */
export function regenerateMessageStream(
  conversationId: string,
  messageId: number,
  callbacks: StreamCallbacks,
): AbortController {
  return fetchSSEStream(
    `/chat/conversations/${conversationId}/messages/regenerate`,
    { message_id: messageId },
    callbacks,
  )
}
