import { useState } from 'react'

export default function CreateRoomModal({ onCreate, onClose }) {
  const [name, setName] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    onCreate(trimmed)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={event => event.stopPropagation()}>
        <h2 className="modal-title">Criar terminal de mesa</h2>
        <form onSubmit={handleSubmit}>
          <input
            autoFocus
            className="modal-input"
            type="text"
            placeholder="Nome da sala ou mesa"
            maxLength={32}
            value={name}
            onChange={event => setName(event.target.value)}
          />
          <div className="modal-help">
            O hub cria a sala e registra automaticamente um terminal MQTT de mesa para controlar os terminais dos jogadores.
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn-confirm" disabled={!name.trim()}>
              Criar mesa
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}