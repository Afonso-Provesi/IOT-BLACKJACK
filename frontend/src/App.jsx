import { useState, useEffect, useCallback } from 'react'
import Table from './components/Table'
import AddPlayerModal from './components/AddPlayerModal'
import { useWebSocket } from './hooks/useWebSocket'
import {
  getState, addPlayer, removePlayer, placeBet,
  startRound, playerHit, playerStand, playerSplit, playerDouble,
  dealerPlay, resetGame, newGame,
} from './api'

export default function App() {
  const [gameState, setGameState] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [isDealing, setIsDealing] = useState(false)
  const [error, setError] = useState(null)
  const { connected, lastMessage } = useWebSocket()

  // Sync game state from WebSocket
  useEffect(() => {
    if (lastMessage?.data) {
      setGameState(lastMessage.data)
    }
  }, [lastMessage])

  // Initial fetch
  useEffect(() => {
    getState().then(state => {
      setGameState(state)
    }).catch(() => {})
  }, [])

  const handleError = (err) => {
    const msg = err?.response?.data?.detail || err?.message || 'Erro desconhecido'
    setError(msg)
    setTimeout(() => setError(null), 4000)
  }

  const handleAddPlayer = useCallback(async (name) => {
    try {
      await addPlayer(name)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleRemovePlayer = useCallback(async (player_id) => {
    try {
      await removePlayer(player_id)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleStartRound = useCallback(async () => {
    try {
      setIsDealing(true)
      await startRound()
      setTimeout(() => setIsDealing(false), 1500)
    } catch (err) {
      setIsDealing(false)
      handleError(err)
    }
  }, [])

  const handleHit = useCallback(async (player_id) => {
    try {
      await playerHit(player_id)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleBet = useCallback(async (player_id, amount) => {
    try {
      await placeBet(player_id, amount)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleStand = useCallback(async (player_id) => {
    try {
      await playerStand(player_id)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleSplit = useCallback(async (player_id) => {
    try {
      await playerSplit(player_id)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleDouble = useCallback(async (player_id) => {
    try {
      await playerDouble(player_id)
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleDealerPlay = useCallback(async () => {
    try {
      setIsDealing(true)
      await dealerPlay()
      setTimeout(() => setIsDealing(false), 2000)
    } catch (err) {
      setIsDealing(false)
      handleError(err)
    }
  }, [])

  const handleReset = useCallback(async () => {
    try {
      await resetGame()
    } catch (err) {
      handleError(err)
    }
  }, [])

  const handleNewGame = useCallback(async () => {
    try {
      await newGame()
    } catch (err) {
      handleError(err)
    }
  }, [])

  return (
    <div className="app-root">
      {/* Header */}
      <header className="app-header">
        <span className="app-title">🃏 Blackjack IoT</span>
        <span className={`ws-status ${connected ? 'ws-on' : 'ws-off'}`}>
          {connected ? '● Online' : '○ Offline'}
        </span>
      </header>

      {/* Error banner */}
      {error && (
        <div className="error-banner">{error}</div>
      )}

      {/* Main table */}
      <main className="app-main">
        <Table
          gameState={gameState}
          onHit={handleHit}
          onStand={handleStand}
          onSplit={handleSplit}
          onDouble={handleDouble}
          onBet={handleBet}
          onRemove={handleRemovePlayer}
          onAddPlayer={() => setShowAddModal(true)}
          onStartRound={handleStartRound}
          onDealerPlay={handleDealerPlay}
          onReset={handleReset}
          onNewGame={handleNewGame}
          isDealing={isDealing}
        />
      </main>

      {/* Add player modal */}
      {showAddModal && (
        <AddPlayerModal
          onAdd={handleAddPlayer}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  )
}
