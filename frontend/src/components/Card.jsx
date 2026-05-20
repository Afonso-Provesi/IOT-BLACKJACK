const SUIT_SYMBOLS = {
  spades: '♠',
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
}

const SUIT_COLORS = {
  spades: '#1a1a2e',
  hearts: '#c0392b',
  diamonds: '#c0392b',
  clubs: '#1a1a2e',
}

export default function Card({ rank, suit, hidden = false, small = false }) {
  const size = small ? 'card-sm' : 'card-md'

  if (hidden) {
    return (
      <div className={`playing-card card-back ${size}`}>
        <div className="card-back-pattern" />
      </div>
    )
  }

  const symbol = SUIT_SYMBOLS[suit] || suit
  const color = SUIT_COLORS[suit] || '#1a1a2e'

  return (
    <div className={`playing-card card-front ${size}`} style={{ color }}>
      <span className="card-corner card-corner-tl">
        <span className="card-rank">{rank}</span>
        <span className="card-suit-small">{symbol}</span>
      </span>
      <span className="card-center-suit">{symbol}</span>
      <span className="card-corner card-corner-br">
        <span className="card-rank">{rank}</span>
        <span className="card-suit-small">{symbol}</span>
      </span>
    </div>
  )
}
