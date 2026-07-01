import { useState, useEffect, useCallback } from 'react'
import Table from './components/Table'
import AddPlayerModal from './components/AddPlayerModal'
import CreateRoomModal from './components/CreateRoomModal'
import HubView from './components/HubView'
import { useWebSocket } from './hooks/useWebSocket'
import {
  getRooms, createRoom, deleteRoom, getState, addPlayer, removePlayer, placeBet,
  startRound, playerHit, playerStand, playerSplit, playerDouble,
  dealerPlay, resetGame, newGame,
} from './api'

const getRoomIdFromLocation = () => {
  const match = window.location.pathname.match(/^\/rooms\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

const navigateToRoom = (roomId, replace = false) => {
  const path = roomId ? `/rooms/${encodeURIComponent(roomId)}` : '/'
  const method = replace ? 'replaceState' : 'pushState'
  window.history[method]({}, '', path)
}

export default function App() {
  const [activeRoomId, setActiveRoomId] = useState(() => getRoomIdFromLocation())
  const [rooms, setRooms] = useState([])
  const [gameState, setGameState] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showCreateRoomModal, setShowCreateRoomModal] = useState(false)
  const [isDealing, setIsDealing] = useState(false)
  const [isLoadingRooms, setIsLoadingRooms] = useState(false)
  const [error, setError] = useState(null)
  const { connected, lastMessage } = useWebSocket(activeRoomId)

  const refreshRooms = useCallback(async () => {
    setIsLoadingRooms(true)
    try {
      const data = await getRooms()
      setRooms(data.rooms ?? [])
    } catch (err) {
      handleError(err)
    } finally {
      setIsLoadingRooms(false)
    }
  }, [])

  // Sync game state from WebSocket
  useEffect(() => {
    if (lastMessage?.data) {
      setGameState(lastMessage.data)
    }
  }, [lastMessage])

  useEffect(() => {
    const handlePopState = () => {
      setActiveRoomId(getRoomIdFromLocation())
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Initial and route-driven fetch
  useEffect(() => {
    if (!activeRoomId) {
      setGameState(null)
      refreshRooms()
      return
    }

    getState(activeRoomId).then(state => {
      setGameState(state)
    }).catch(err => {
      handleError(err)
      setActiveRoomId(null)
      navigateToRoom(null, true)
    })
  }, [activeRoomId, refreshRooms])

  const handleError = (err) => {
    const msg = err?.response?.data?.detail || err?.message || 'Erro desconhecido'
    setError(msg)
    setTimeout(() => setError(null), 4000)
  }

  const handleOpenRoom = useCallback((roomId) => {
    setActiveRoomId(roomId)
    navigateToRoom(roomId)
  }, [])

  const handleBackToHub = useCallback(() => {
    setShowAddModal(false)
    setActiveRoomId(null)
    navigateToRoom(null)
    refreshRooms()
  }, [refreshRooms])

  const handleCreateRoom = useCallback(async (name) => {
    try {
      const data = await createRoom(name)
      const nextRoom = data.room
      setRooms(prev => {
        const filtered = prev.filter(room => room.room_id !== nextRoom.room_id)
        return [...filtered, nextRoom]
      })
      setShowCreateRoomModal(false)
      handleOpenRoom(nextRoom.room_id)
    } catch (err) {
      handleError(err)
    }
  }, [handleOpenRoom])

  const handleDeleteRoom = useCallback(async (roomId) => {
    if (!window.confirm('Excluir esta mesa e todos os terminais associados?')) {
      return
    }

    try {
      await deleteRoom(roomId)
      setRooms(prev => prev.filter(room => room.room_id !== roomId))

      if (activeRoomId === roomId) {
        setGameState(null)
        setActiveRoomId(null)
        navigateToRoom(null)
      }
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleAddPlayer = useCallback(async (name) => {
    try {
      await addPlayer(name, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleRemovePlayer = useCallback(async (player_id) => {
    try {
      await removePlayer(player_id, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleStartRound = useCallback(async () => {
    try {
      setIsDealing(true)
      await startRound(activeRoomId)
      setTimeout(() => setIsDealing(false), 1500)
    } catch (err) {
      setIsDealing(false)
      handleError(err)
    }
  }, [activeRoomId])

  const handleHit = useCallback(async (player_id) => {
    try {
      await playerHit(player_id, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleBet = useCallback(async (player_id, amount) => {
    try {
      await placeBet(player_id, amount, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleStand = useCallback(async (player_id) => {
    try {
      await playerStand(player_id, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleSplit = useCallback(async (player_id) => {
    try {
      await playerSplit(player_id, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleDouble = useCallback(async (player_id) => {
    try {
      await playerDouble(player_id, activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleDealerPlay = useCallback(async () => {
    try {
      setIsDealing(true)
      await dealerPlay(activeRoomId)
      setTimeout(() => setIsDealing(false), 2000)
    } catch (err) {
      setIsDealing(false)
      handleError(err)
    }
  }, [activeRoomId])

  const handleReset = useCallback(async () => {
    try {
      await resetGame(activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const handleNewGame = useCallback(async () => {
    try {
      await newGame(activeRoomId)
    } catch (err) {
      handleError(err)
    }
  }, [activeRoomId])

  const roomLabel = gameState?.room_name || rooms.find(room => room.room_id === activeRoomId)?.name || 'Mesa'
  const tableTerminalId = gameState?.table_terminal_id || rooms.find(room => room.room_id === activeRoomId)?.table_terminal_id

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-header-main">
          <span className="app-title">🃏 Blackjack IoT</span>
          {activeRoomId && (
            <div className="app-room-meta">
              <button className="btn-back-hub" onClick={handleBackToHub}>
                Hub
              </button>
              {activeRoomId && activeRoomId !== 'mesa-principal' && (
                <button className="btn-delete-room" onClick={() => handleDeleteRoom(activeRoomId)}>
                  Excluir mesa
                </button>
              )}
              <div className="room-meta-copy">
                <strong>{roomLabel}</strong>
                <span>{tableTerminalId}</span>
              </div>
            </div>
          )}
        </div>
        <span className={`ws-status ${activeRoomId && connected ? 'ws-on' : 'ws-off'}`}>
          {activeRoomId ? (connected ? '● Mesa online' : '○ Mesa offline') : '○ Hub local'}
        </span>
      </header>

      {error && (
        <div className="error-banner">{error}</div>
      )}

      <main className="app-main">
        {activeRoomId ? (
          <div className="room-screen">
            <section className="room-terminal-panel">
              <div>
                <div className="room-terminal-label">Terminal da mesa</div>
                <div className="room-terminal-id">{tableTerminalId}</div>
              </div>
              <div className="room-terminal-topics">
                <span>{`state: blackjack/rooms/${activeRoomId}/game/state`}</span>
                <span>{`mesa: blackjack/rooms/${activeRoomId}/tables/${tableTerminalId}/action`}</span>
                <span>{`jogadores: blackjack/rooms/${activeRoomId}/players/{player_id}/action`}</span>
              </div>
            </section>
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
          </div>
        ) : (
          <HubView
            rooms={rooms}
            isLoading={isLoadingRooms}
            onCreateRoom={() => setShowCreateRoomModal(true)}
            onOpenRoom={handleOpenRoom}
            onRefresh={refreshRooms}
            onDeleteRoom={handleDeleteRoom}
          />
        )}
      </main>

      {showAddModal && (
        <AddPlayerModal
          onAdd={handleAddPlayer}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {showCreateRoomModal && (
        <CreateRoomModal
          onCreate={handleCreateRoom}
          onClose={() => setShowCreateRoomModal(false)}
        />
      )}
    </div>
  )
}
