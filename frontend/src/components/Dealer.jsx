import Card from './Card'

export default function Dealer({ dealer, isDealing }) {
  return (
    <div className="dealer-area">
      {/* Robot SVG */}
      <div className={`robot-container ${isDealing ? 'robot-dealing' : 'robot-idle'}`}>
        <svg viewBox="0 0 120 180" className="robot-svg" xmlns="http://www.w3.org/2000/svg">
          {/* Antenna */}
          <line x1="60" y1="12" x2="60" y2="0" stroke="#7f8c8d" strokeWidth="4" strokeLinecap="round" />
          <circle cx="60" cy="0" r="6" fill="#f39c12" className="antenna-glow" />

          {/* Head */}
          <rect x="30" y="12" width="60" height="52" rx="12" fill="#2c3e50" />
          <rect x="35" y="17" width="50" height="42" rx="8" fill="#34495e" />

          {/* Eyes */}
          <ellipse cx="47" cy="36" rx="9" ry="9" fill="#1abc9c" className="eye-glow" />
          <ellipse cx="73" cy="36" rx="9" ry="9" fill="#1abc9c" className="eye-glow" />
          <ellipse cx="47" cy="36" rx="5" ry="5" fill="white" opacity="0.9" />
          <ellipse cx="73" cy="36" rx="5" ry="5" fill="white" opacity="0.9" />
          <circle cx="47" cy="36" r="2.5" fill="#0d7377" />
          <circle cx="73" cy="36" r="2.5" fill="#0d7377" />

          {/* Mouth */}
          <rect x="40" y="52" width="40" height="6" rx="3" fill="#1abc9c" />

          {/* Neck */}
          <rect x="52" y="64" width="16" height="10" rx="4" fill="#2c3e50" />

          {/* Body */}
          <rect x="20" y="74" width="80" height="72" rx="12" fill="#2c3e50" />
          <rect x="28" y="82" width="64" height="54" rx="8" fill="#34495e" />

          {/* Chest panel */}
          <rect x="36" y="90" width="48" height="36" rx="6" fill="#1a252f" />
          <circle cx="48" cy="102" r="7" fill="#e74c3c" opacity="0.9" />
          <circle cx="60" cy="102" r="7" fill="#f39c12" opacity="0.9" />
          <circle cx="72" cy="102" r="7" fill="#2ecc71" opacity="0.9" />
          <rect x="40" y="116" width="40" height="5" rx="2" fill="#1abc9c" opacity="0.7" />

          {/* Left arm */}
          <rect
            x="2" y="78" width="18" height="42" rx="9"
            fill="#2c3e50"
            className="arm-left"
            style={{ transformOrigin: '11px 78px' }}
          />
          {/* Left hand */}
          <circle cx="11" cy="124" r="7" fill="#34495e" className="arm-left" style={{ transformOrigin: '11px 78px' }} />

          {/* Right arm */}
          <rect
            x="100" y="78" width="18" height="42" rx="9"
            fill="#2c3e50"
            className="arm-right"
            style={{ transformOrigin: '109px 78px' }}
          />
          {/* Right hand */}
          <circle cx="109" cy="124" r="7" fill="#34495e" className="arm-right" style={{ transformOrigin: '109px 78px' }} />

          {/* Legs */}
          <rect x="32" y="145" width="22" height="28" rx="10" fill="#2c3e50" />
          <rect x="66" y="145" width="22" height="28" rx="10" fill="#2c3e50" />

          {/* Feet */}
          <ellipse cx="43" cy="172" rx="14" ry="7" fill="#1a252f" />
          <ellipse cx="77" cy="172" rx="14" ry="7" fill="#1a252f" />
        </svg>
      </div>

      {/* Dealer label */}
      <div className="dealer-label">🤖 Dealer</div>

      {/* Dealer hand */}
      <div className="dealer-hand">
        {dealer?.hand?.length > 0 ? (
          <>
            <div className="player-hand" style={{ justifyContent: 'center' }}>
              {dealer.hand.map((card, i) => (
                <div
                  key={i}
                  className="card-wrapper"
                  style={{ zIndex: i, marginLeft: i > 0 ? '-28px' : '0' }}
                >
                  <Card rank={card.rank} suit={card.suit} hidden={card.hidden} />
                </div>
              ))}
            </div>
            {!dealer.hand.every(c => c.hidden) && (
              <div className="hand-value dealer-value">{dealer.hand_value}</div>
            )}
          </>
        ) : (
          <div className="empty-hand" style={{ color: '#7f8c8d' }}>Dealer</div>
        )}
      </div>
    </div>
  )
}
