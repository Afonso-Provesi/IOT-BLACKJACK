import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL ||
  (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'

export function useWebSocket() {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)

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
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected, lastMessage }
}
