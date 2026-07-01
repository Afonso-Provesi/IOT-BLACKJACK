import { useEffect, useRef, useState, useCallback } from 'react'

const DEFAULT_WS_URL = import.meta.env.VITE_WS_URL ||
  (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'

const getWsUrl = (roomId) => {
  if (!roomId) return DEFAULT_WS_URL

  const separator = DEFAULT_WS_URL.includes('?') ? '&' : '?'
  return `${DEFAULT_WS_URL}${separator}room_id=${encodeURIComponent(roomId)}`
}

export function useWebSocket(roomId) {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const reconnectTimer = useRef(null)

  const enabled = Boolean(roomId)

  const connect = useCallback(() => {
    if (!enabled) {
      setConnected(false)
      return
    }

    try {
      const ws = new WebSocket(getWsUrl(roomId))

      ws.onopen = () => {
        setConnected(true)
        console.log('[WS] Conectado')
      }

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data)
          setLastMessage(data)
        } catch (e) {
          console.warn('[WS] Mensagem inválida:', e)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        console.warn('[WS] Desconectado. Reconectando em 3s...')
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = (err) => {
        console.error('[WS] Erro:', err)
        ws.close()
      }

      wsRef.current = ws
    } catch (e) {
      console.error('[WS] Falha ao criar WebSocket:', e)
      reconnectTimer.current = setTimeout(connect, 3000)
    }
  }, [enabled, roomId])

  useEffect(() => {
    if (!enabled) {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
      return undefined
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect, enabled])

  return { connected, lastMessage }
}
