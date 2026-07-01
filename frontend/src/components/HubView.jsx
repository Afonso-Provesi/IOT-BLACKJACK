const getStatusLabel = (status) => {
  if (status === 'waiting') return 'Aguardando apostas'
  if (status === 'player_turn') return 'Jogadores em turno'
  if (status === 'dealer_turn') return 'Dealer em turno'
  if (status === 'finished') return 'Rodada encerrada'
  return 'Em preparação'
}

export default function HubView({ rooms, isLoading, onCreateRoom, onOpenRoom, onRefresh, onDeleteRoom }) {
  return (
    <section className="hub-screen">
      <div className="hub-hero">
        <div>
          <div className="hub-kicker">Hub MQTT</div>
          <h1 className="hub-title">Gerencie multiplas mesas e seus terminais filhos</h1>
          <p className="hub-copy">
            Cada sala cria um terminal de mesa próprio. Esse terminal coordena a rodada e conversa com os terminais menores de jogadores via tópicos MQTT isolados por sala.
          </p>
        </div>
        <div className="hub-actions">
          <button className="hub-primary-button" onClick={onCreateRoom}>
            Nova mesa terminal
          </button>
          <button className="hub-secondary-button" onClick={onRefresh}>
            Atualizar hub
          </button>
        </div>
      </div>

      <div className="hub-grid">
        {rooms.map(room => (
          <article key={room.room_id} className="hub-card">
            <div className="hub-card-header">
              <div>
                <div className="hub-card-title">{room.name}</div>
                <div className="hub-card-subtitle">{room.room_id}</div>
              </div>
              <span className="hub-card-status">{getStatusLabel(room.status)}</span>
            </div>

            <div className="hub-card-metrics">
              <div>
                <strong>{room.player_count}</strong>
                <span>terminais de jogador</span>
              </div>
              <div>
                <strong>{room.active_player_count}</strong>
                <span>jogadores ativos</span>
              </div>
              <div>
                <strong>{room.deck_remaining}</strong>
                <span>cartas restantes</span>
              </div>
            </div>

            <div className="hub-card-topics">
              <div>
                <span className="hub-topic-label">Mesa</span>
                <code>{room.table_terminal_id}</code>
              </div>
              <div>
                <span className="hub-topic-label">Estado</span>
                <code>{`blackjack/rooms/${room.room_id}/game/state`}</code>
              </div>
              <div>
                <span className="hub-topic-label">Acoes da mesa</span>
                <code>{`blackjack/rooms/${room.room_id}/tables/${room.table_terminal_id}/action`}</code>
              </div>
              <div>
                <span className="hub-topic-label">Acoes dos jogadores</span>
                <code>{`blackjack/rooms/${room.room_id}/players/{player_id}/action`}</code>
              </div>
            </div>

            <div className="hub-card-actions">
              <button className="hub-open-button" onClick={() => onOpenRoom(room.room_id)}>
                Abrir mesa
              </button>
              {room.room_id !== 'mesa-principal' && (
                <button className="hub-delete-button" onClick={() => onDeleteRoom(room.room_id)}>
                  Excluir mesa
                </button>
              )}
            </div>
          </article>
        ))}

        {!rooms.length && !isLoading && (
          <div className="hub-empty-state">
            <div className="hub-empty-title">Nenhuma mesa criada</div>
            <p>Crie a primeira sala no hub para registrar um terminal de mesa e começar a adicionar terminais de jogadores.</p>
            <button className="hub-primary-button" onClick={onCreateRoom}>
              Criar primeira mesa
            </button>
          </div>
        )}
      </div>

      {isLoading && <div className="hub-loading">Sincronizando salas e terminais...</div>}
    </section>
  )
}