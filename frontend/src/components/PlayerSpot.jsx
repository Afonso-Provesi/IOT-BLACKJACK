import { useEffect, useRef, useState } from 'react'
import Card from './Card'
import { useCardSound } from '../hooks/useSound'
const STATUS_LABELS = {
  waiting: '',
  playing: '',
  stood: 'PAROU',
  bust: 'BUST',
  blackjack: 'BLACKJACK!',
  win: 'GANHOU',
  lose: 'PERDEU',
  tie: 'EMPATE',
}

const STATUS_COLORS = {
  waiting: '',
  playing: 'text-white',
  stood: 'text-yellow-300',
  bust: 'text-red-400',
  blackjack: 'text-yellow-300',
  win: 'text-green-400',
  lose: 'text-red-400',
  tie: 'text-gray-300',
}

export default function PlayerSpot({
  player,
  onHit,
  onStand,
  onBet,
  onRemove,
  onSplit,
  onDouble,
  isMyTurn,
  gameStatus,
  position,
}) {
  const { playDeal } = useCardSound()
  const prevHandLen = useRef(0)
  const prevSplitHandLen = useRef(-1)  // -1 = no split hand
  const splitDelayOffsetRef = useRef(0)
  const [dealingSet, setDealingSet] = useState(() => new Set())
  const [splitDealingSet, setSplitDealingSet] = useState(() => new Set())
  const [betInput, setBetInput] = useState('')

  const dealX = position ? `${Math.round((50 - position[0]) * 7.5)}px` : '0px'
  const dealY = position ? `${Math.round((position[1] - 6) * -5.2)}px` : '-360px'
  const dealRot = position && position[0] < 50 ? '560deg' : '-560deg'

  const splitLen = player.split_hand?.length ?? -1

  useEffect(() => {
    const currMainLen = player.hand.length
    const currSplitLen = splitLen
    const prevMainLen = prevHandLen.current
    const prevSplitLen = prevSplitHandLen.current

    // ── Reset when hand cleared (new round) ──────────────────────
    if (currMainLen === 0) {
      prevHandLen.current = 0
      prevSplitHandLen.current = -1
      splitDelayOffsetRef.current = 0
      setDealingSet(new Set())
      setSplitDealingSet(new Set())
      setBetInput('')
      return
    }

    // ── Split just happened ────────────────────────────────────────
    if (prevSplitLen === -1 && currSplitLen >= 0) {
      const h1Set = new Set(Array.from({ length: currMainLen }, (_, i) => i))
      const h2Set = new Set(Array.from({ length: currSplitLen }, (_, i) => i))
      setDealingSet(h1Set)
      setSplitDealingSet(h2Set)
      splitDelayOffsetRef.current = currMainLen  // split hand plays after main hand
      const total = currMainLen + currSplitLen
      for (let i = 0; i < total; i++) playDeal(i * 0.18)
      const tid = setTimeout(() => {
        setDealingSet(new Set())
        setSplitDealingSet(new Set())
      }, 600 + (total - 1) * 180)
      prevHandLen.current = currMainLen
      prevSplitHandLen.current = currSplitLen
      return () => clearTimeout(tid)
    }

    // ── Split hand disappeared (reset) ────────────────────────────
    if (currSplitLen === -1 && prevSplitLen >= 0) {
      prevSplitHandLen.current = -1
      splitDelayOffsetRef.current = 0
      setSplitDealingSet(new Set())
      // fall through to check main hand
    }

    // ── Main hand grew ────────────────────────────────────────────
    if (currMainLen > prevMainLen) {
      const newSet = new Set()
      for (let i = prevMainLen; i < currMainLen; i++) newSet.add(i)
      setDealingSet(newSet)
      splitDelayOffsetRef.current = 0
      let rel = 0
      newSet.forEach(() => { playDeal(rel * 0.18); rel++ })
      const tid = setTimeout(() => setDealingSet(new Set()), 600 + (newSet.size - 1) * 180)
      prevHandLen.current = currMainLen
      prevSplitHandLen.current = currSplitLen
      return () => clearTimeout(tid)
    }

    // ── Split hand grew (hit on Mão 2) ────────────────────────────
    if (currSplitLen > prevSplitLen && prevSplitLen >= 0) {
      const newSet = new Set()
      for (let i = prevSplitLen; i < currSplitLen; i++) newSet.add(i)
      setSplitDealingSet(newSet)
      splitDelayOffsetRef.current = 0
      let rel = 0
      newSet.forEach(() => { playDeal(rel * 0.18); rel++ })
      const tid = setTimeout(() => setSplitDealingSet(new Set()), 600 + (newSet.size - 1) * 180)
      prevSplitHandLen.current = currSplitLen
      return () => clearTimeout(tid)
    }

    prevHandLen.current = currMainLen
    prevSplitHandLen.current = currSplitLen
  }, [player.hand.length, splitLen, playDeal])

  const statusLabel = STATUS_LABELS[player.status] || ''
  const statusColor = STATUS_COLORS[player.status] || ''
  const hasSplit = !!player.split_hand
  const activeStatus = player.active_hand_idx === 0
    ? player.status
    : (player.split_status || player.status)
  const canAct = isMyTurn && activeStatus === 'playing' && !player.eliminated
  const isBettingPhase = (gameStatus === 'waiting' || gameStatus === 'finished') && !player.eliminated
  const hasBet = player.bet > 0

  const submitBet = () => {
    const amount = parseInt(betInput, 10)
    if (amount > 0 && amount <= player.balance) {
      onBet(player.player_id, amount)
      setBetInput('')
    }
  }

  const quickBet = (amount) => {
    const capped = Math.min(amount, player.balance)
    onBet(player.player_id, capped)
  }

  return (
    <div className={`player-spot${player.eliminated ? ' player-eliminated' : ''}`}>
      {/* Name + balance */}
      <div className="player-name">
        <span>{player.name}</span>
        {isBettingPhase && !player.eliminated && (
          <button className="remove-btn" onClick={() => onRemove(player.player_id)} title="Remover">×</button>
        )}
      </div>
      <div className="player-balance">
        💰 {player.balance ?? 500}
        {hasBet && <span className="bet-badge">Aposta: {player.bet}</span>}
      </div>

      {/* Betting controls */}
      {isBettingPhase && !hasBet && (
        <div className="bet-controls">
          <div className="bet-quick">
            {[10, 25, 50, 100].filter(v => v <= player.balance).map(v => (
              <button key={v} className="btn-quick-bet" onClick={() => quickBet(v)}>{v}</button>
            ))}
            <button className="btn-quick-bet btn-allin" onClick={() => quickBet(player.balance)}>All‑in</button>
          </div>
          <div className="bet-input-row">
            <input
              className="bet-input"
              type="number"
              min="1"
              max={player.balance}
              placeholder="valor"
              value={betInput}
              onChange={e => setBetInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submitBet()}
            />
            <button className="btn-bet-confirm" onClick={submitBet}>Apostar</button>
          </div>
        </div>
      )}

      {/* Eliminated message */}
      {player.eliminated && (
        <div className="eliminated-msg">Sem saldo — eliminado</div>
      )}

      {/* Main hand */}
      <div className={`hand-section${player.active_hand_idx === 0 ? ' hand-section-active' : ''}`}>
        {hasSplit && (
          <div className="hand-section-label">
            Mão 1
            {player.bet > 0 && <span className="bet-badge-sm">{player.bet}</span>}
          </div>
        )}
        <div className="player-hand">
          {player.hand.length === 0 ? (
            <div className="empty-hand">{hasBet ? 'aguardando início...' : ''}</div>
          ) : (
            player.hand.map((card, i) => {
              const isDealing = dealingSet.has(i)
              return (
                <div
                  key={i}
                  className={`card-wrapper${isDealing ? ' card-dealing' : ''}`}
                  style={{
                    zIndex: isDealing ? 50 : i,
                    marginLeft: i > 0 ? '-28px' : '0',
                    ...(isDealing && {
                      '--deal-x': dealX,
                      '--deal-y': dealY,
                      '--deal-rot': dealRot,
                      animationDelay: `${(i - (player.hand.length - dealingSet.size)) * 0.18}s`,
                    }),
                  }}
                >
                  <Card rank={card.rank} suit={card.suit} hidden={card.hidden} small />
                </div>
              )
            })
          )}
        </div>
        {player.hand.length > 0 && !player.hand.every(c => c.hidden) && (
          <div className="hand-value">{player.hand_value}</div>
        )}
        {statusLabel && (
          <div className={`status-badge ${statusColor}`}>{statusLabel}</div>
        )}
      </div>

      {/* Split hand */}
      {hasSplit && (
        <div className={`hand-section${player.active_hand_idx === 1 ? ' hand-section-active' : ''}`}>
          <div className="hand-section-label">
            Mão 2
            {player.split_bet > 0 && <span className="bet-badge-sm">{player.split_bet}</span>}
          </div>
          <div className="player-hand">
            {player.split_hand.map((card, i) => {
              const isDealing = splitDealingSet.has(i)
              return (
                <div
                  key={i}
                  className={`card-wrapper${isDealing ? ' card-dealing' : ''}`}
                  style={{
                    zIndex: isDealing ? 50 : i,
                    marginLeft: i > 0 ? '-28px' : '0',
                    ...(isDealing && {
                      '--deal-x': dealX,
                      '--deal-y': dealY,
                      '--deal-rot': dealRot,
                      animationDelay: `${(i - (player.split_hand.length - splitDealingSet.size)) * 0.18 + splitDelayOffsetRef.current * 0.18}s`,
                    }),
                  }}
                >
                  <Card rank={card.rank} suit={card.suit} hidden={card.hidden} small />
                </div>
              )
            })}
          </div>
          {player.split_hand.length > 0 && !player.split_hand.every(c => c.hidden) && (
            <div className="hand-value">{player.split_hand_value}</div>
          )}
          {player.split_status && (
            <div className={`status-badge ${STATUS_COLORS[player.split_status] || ''}`}>
              {STATUS_LABELS[player.split_status] || ''}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      {canAct && (
        <div className="action-buttons">
          <button className="btn-hit" onClick={() => onHit(player.player_id)}>Pedir Carta</button>
          <button className="btn-stand" onClick={() => onStand(player.player_id)}>Parar</button>
          {player.can_double && (
            <button className="btn-double" onClick={() => onDouble(player.player_id)}>2× Dobrar</button>
          )}
          {player.can_split && (
            <button className="btn-split" onClick={() => onSplit(player.player_id)}>Split</button>
          )}
        </div>
      )}
    </div>
  )
}
