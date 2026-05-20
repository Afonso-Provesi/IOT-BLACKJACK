import Dealer from './Dealer'
import PlayerSpot from './PlayerSpot'

// Positions for players arranged in a semicircle (% of table width/height)
// [x%, y%] — for 1–6 players
const POSITIONS = {
  1: [[50, 82]],
  2: [[25, 80], [75, 80]],
  3: [[12, 67], [50, 84], [88, 67]],
  4: [[8, 58],  [30, 81], [70, 81], [92, 58]],
}

export default function Table({
  gameState,
  onHit,
  onStand,
  onSplit,
  onDouble,
  onBet,
  onRemove,
  onAddPlayer,
  onStartRound,
  onDealerPlay,
  onReset,
  onNewGame,
  isDealing,
}) {
  const players = gameState?.players ?? []
  const dealer = gameState?.dealer
  const status = gameState?.status ?? 'waiting'
  const gameOverReason = gameState?.game_over_reason ?? null
  const gameOverWinner = gameState?.game_over_winner ?? null
  const count = Math.min(players.length, 4)
  const positions = POSITIONS[count] || POSITIONS[4]

  const canStart = status === 'waiting' && players.length > 0 &&
    players.every(p => p.eliminated || p.bet > 0)
  const canAddPlayer = (status === 'waiting' || status === 'finished') && players.length < 4 && !gameOverReason
  const allDone = players.length > 0 && players.every(p => p.status !== 'playing')
  const canDealerPlay = status === 'player_turn' && allDone
  const canReset = status === 'finished' && !gameOverReason

  return (
    <div className="table-wrapper">
      {/* Green felt table */}
      <div className="felt-table">
        {/* Table inner oval */}
        <div className="table-inner">

          {/* Dealer zone at top */}
          <div className="dealer-zone">
            <Dealer dealer={dealer} isDealing={isDealing} />
          </div>

          {/* Center: game controls */}
          <div className="center-controls">
            {canStart && (
              <button className="btn-deal" onClick={onStartRound}>
                ▶ Distribuir Cartas
              </button>
            )}
            {canDealerPlay && (
              <button className="btn-dealer-play" onClick={onDealerPlay}>
                🤖 Vez do Dealer
              </button>
            )}
            {canReset && (
              <button className="btn-new-round" onClick={onReset}>
                🔄 Nova Rodada
              </button>
            )}
            {status === 'player_turn' && !allDone && (
              <div className="turn-indicator">Aguardando jogadores...</div>
            )}
            {status === 'dealer_turn' && (
              <div className="turn-indicator">Dealer jogando...</div>
            )}
          </div>

          {/* Player spots positioned around the arc */}
          {players.slice(0, 4).map((player, i) => {
            const [x, y] = positions[i] || [50, 80]
            return (
              <div
                key={player.player_id}
                className="player-spot-wrapper"
                style={{ left: `${x}%`, top: `${y}%` }}
              >
                <PlayerSpot
                  player={player}
                  onHit={onHit}
                  onStand={onStand}
                  onSplit={onSplit}
                  onDouble={onDouble}
                  onBet={onBet}
                  onRemove={onRemove}
                  isMyTurn={status === 'player_turn'}
                  gameStatus={status}
                  position={positions[i]}
                />
              </div>
            )
          })}

          {/* Game-over overlay */}
          {gameOverReason && (
            <div className="game-over-overlay">
              <div className="game-over-card">
                {gameOverReason === 'house_wins' ? (
                  <>
                    <div className="game-over-icon">🏦</div>
                    <div className="game-over-title">Mesa Venceu</div>
                    <div className="game-over-sub">Sem mais jogadores com saldo</div>
                  </>
                ) : (
                  <>
                    <div className="game-over-icon">🏆</div>
                    <div className="game-over-title">{gameOverWinner} Venceu!</div>
                    <div className="game-over-sub">Último jogador em pé</div>
                  </>
                )}
                <button className="btn-new-game" onClick={onNewGame}>
                  Nova Partida
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="table-toolbar">
        {canAddPlayer && (
          <button className="btn-add-player" onClick={onAddPlayer}>
            + Adicionar Terminal
          </button>
        )}
        <div className="deck-info">
          🃏 {gameState?.deck_remaining ?? 52} cartas
        </div>
      </div>
    </div>
  )
}
