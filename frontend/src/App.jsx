import { useState, useEffect, useCallback } from 'react'
import StatusBar from './components/StatusBar'
import ImageUploader from './components/ImageUploader'
import ResultPanel from './components/ResultPanel'
import HistoryList from './components/HistoryList'
import { useWebSocket } from './hooks/useWebSocket'
import { getHealth, getHistory, clearHistory } from './api'

export default function App() {
  const { connected: wsConnected, lastMessage } = useWebSocket()

  const [mqttConnected, setMqttConnected] = useState(false)
  const [currentResult, setCurrentResult] = useState(null)
  const [history, setHistory] = useState([])
  const [logs, setLogs] = useState([])

  // Polling de saúde a cada 5s
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await getHealth()
        setMqttConnected(res.data.mqtt_connected)
      } catch {
        setMqttConnected(false)
      }
    }
    poll()
    const id = setInterval(poll, 5000)
    return () => clearInterval(id)
  }, [])

  // Carrega histórico inicial
  const loadHistory = useCallback(async () => {
    try {
      const res = await getHistory()
      setHistory(res.data.results ?? [])
    } catch (e) {
      console.warn('Erro ao carregar histórico:', e)
    }
  }, [])

  useEffect(() => { loadHistory() }, [loadHistory])

  // Resultado via WebSocket (tempo real)
  useEffect(() => {
    if (!lastMessage) return
    setCurrentResult(lastMessage)
    setHistory((prev) => [lastMessage, ...prev].slice(0, 100))
    addLog(`[WS] Frame ${lastMessage.frame_id} — ${lastMessage.cards_detected} carta(s), total ${lastMessage.total_value}`)
  }, [lastMessage])

  const addLog = (msg) => {
    const ts = new Date().toLocaleTimeString('pt-BR')
    setLogs((prev) => [`[${ts}] ${msg}`, ...prev].slice(0, 50))
  }

  const handleUploadResult = (result) => {
    setCurrentResult(result)
    setHistory((prev) => [result, ...prev].slice(0, 100))
    addLog(`[Upload] Frame ${result.frame_id} — ${result.cards_detected} carta(s), total ${result.total_value}`)
  }

  const handleClearHistory = async () => {
    await clearHistory()
    setHistory([])
    addLog('[Sistema] Histórico limpo.')
  }

  return (
    <div className="min-h-screen bg-felt-dark text-white flex flex-col">
      {/* Header */}
      <header className="bg-felt border-b border-green-900 px-6 py-4 flex items-center justify-between shadow-lg">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-wide">
            ♠ Blackjack Vision IoT
          </h1>
          <p className="text-xs text-green-300 mt-0.5">Detecção de cartas via MQTT + Computer Vision</p>
        </div>
        <StatusBar mqttConnected={mqttConnected} wsConnected={wsConnected} />
      </header>

      {/* Main */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">

        {/* Coluna 1 — Upload */}
        <section className="bg-black/30 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-green-300">📷 Simular Câmera</h2>
          <p className="text-xs text-gray-400">
            Envie uma imagem de carta. O sistema publicará via MQTT e retornará o resultado da detecção.
          </p>
          <ImageUploader onResult={handleUploadResult} />
        </section>

        {/* Coluna 2 — Resultado atual */}
        <section className="bg-black/30 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-green-300">🃏 Resultado Atual</h2>
          <ResultPanel result={currentResult} />
        </section>

        {/* Coluna 3 — Histórico */}
        <section className="bg-black/30 border border-white/10 rounded-2xl p-5 flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-green-300">📋 Histórico</h2>
          <HistoryList items={history} onClear={handleClearHistory} />
        </section>

      </main>

      {/* Log console */}
      <footer className="bg-black/50 border-t border-white/10 px-4 py-3">
        <p className="text-xs text-green-400 mb-1 font-mono font-semibold">LOGS</p>
        <div className="max-h-28 overflow-y-auto space-y-0.5">
          {logs.length === 0 && (
            <p className="text-xs text-gray-600 font-mono">Aguardando eventos...</p>
          )}
          {logs.map((log, i) => (
            <p key={i} className="text-xs text-gray-300 font-mono">{log}</p>
          ))}
        </div>
      </footer>
    </div>
  )
}
