export function suitSymbol(suit) {
  const map = {
    spades: '♠',
    hearts: '♥',
    diamonds: '♦',
    clubs: '♣',
    hearts_or_diamonds: '♥/♦',
    spades_or_clubs: '♠/♣',
  }
  return map[suit] ?? '?'
}

export function isRedSuit(suit) {
  return suit === 'hearts' || suit === 'diamonds' || suit === 'hearts_or_diamonds'
}

export function bjValueColor(value) {
  if (value > 21) return 'text-red-500'
  if (value === 21) return 'text-yellow-400'
  if (value >= 17) return 'text-orange-400'
  return 'text-green-400'
}

export function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleTimeString('pt-BR')
}
