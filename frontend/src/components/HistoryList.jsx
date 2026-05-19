import { formatTime, suitSymbol, isRedSuit, bjValueColor } from '../utils/cardUtils'
import { Trash2 } from 'lucide-react'

export default function HistoryList({ items, onClear }) {
  if (!items || items.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-6">Sem histórico ainda.</p>
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-gray-400">{items.length} resultado(s)</span>
        <button
          onClick={onClear}
          className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition"
        >
          <Trash2 className="w-3 h-3" /> Limpar
        </button>
      </div>

      <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
        {items.map((r, i) => (
          <div
            key={r.frame_id ?? i}
            className="bg-black/30 rounded-lg p-3 flex items-center justify-between gap-2 text-sm border border-white/5"
          >
            <div className="flex items-center gap-2 flex-wrap">
              {r.cards?.map((c, j) => (
                <span key={j} className={`font-semibold ${isRedSuit(c.suit) ? 'text-red-400' : 'text-gray-200'}`}>
                  {c.rank ?? '?'}{suitSymbol(c.suit)}
                </span>
              ))}
              {(!r.cards || r.cards.length === 0) && (
                <span className="text-gray-500 italic">sem cartas</span>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className={`font-bold ${bjValueColor(r.total_value)}`}>{r.total_value}</span>
              <span className="text-gray-500 text-xs">{formatTime(r.timestamp)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
