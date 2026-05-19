import { suitSymbol, isRedSuit } from '../utils/cardUtils'

export default function CardBadge({ rank, suit, value, confidence }) {
  const red = isRedSuit(suit)
  return (
    <div className="bg-white rounded-xl shadow-lg p-4 flex flex-col items-center gap-1 min-w-[90px] border border-gray-200 slide-in">
      <span className={`text-4xl font-bold font-display ${red ? 'text-red-500' : 'text-gray-900'}`}>
        {rank ?? '?'}
      </span>
      <span className={`text-3xl ${red ? 'text-red-500' : 'text-gray-900'}`}>
        {suitSymbol(suit)}
      </span>
      <span className="text-xs text-gray-500 mt-1">Val: <strong>{value}</strong></span>
      {confidence != null && (
        <span className="text-[10px] text-gray-400">{(confidence * 100).toFixed(1)}%</span>
      )}
    </div>
  )
}
