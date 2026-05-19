import { bjValueColor, formatTime } from '../utils/cardUtils'
import CardBadge from './CardBadge'

export default function ResultPanel({ result }) {
  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-400 gap-2">
        <span className="text-5xl">🂠</span>
        <p>Aguardando detecção...</p>
      </div>
    )
  }

  const { cards = [], total_value, cards_detected, processing_time_s, timestamp, frame_id, status } = result

  return (
    <div className="space-y-4 slide-in">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between text-sm text-gray-300">
        <span>Frame <code className="bg-black/30 px-1 rounded">{frame_id}</code></span>
        <span>{formatTime(timestamp)}</span>
      </div>

      {/* Status */}
      {status === 'no_cards_detected' ? (
        <div className="bg-yellow-900/40 border border-yellow-600 rounded-lg p-3 text-yellow-300 text-sm">
          Nenhuma carta detectada neste frame.
        </div>
      ) : (
        <>
          {/* Cartas */}
          <div className="flex flex-wrap gap-3">
            {cards.map((c, i) => (
              <CardBadge
                key={i}
                rank={c.rank}
                suit={c.suit}
                value={c.blackjack_value}
                confidence={c.confidence}
              />
            ))}
          </div>

          {/* Total */}
          <div className="flex items-center gap-3 mt-2">
            <span className="text-gray-300 text-sm">Total Blackjack:</span>
            <span className={`text-3xl font-bold ${bjValueColor(total_value)}`}>
              {total_value}
            </span>
            {total_value === 21 && <span className="text-yellow-400 font-bold">BLACKJACK! 🎉</span>}
            {total_value > 21 && <span className="text-red-500 font-bold">BUST!</span>}
          </div>
        </>
      )}

      {/* Métricas */}
      <div className="text-xs text-gray-500 flex gap-4">
        <span>{cards_detected} carta(s)</span>
        <span>{processing_time_s}s</span>
      </div>
    </div>
  )
}
