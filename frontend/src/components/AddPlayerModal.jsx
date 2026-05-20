import { useState } from 'react'

export default function AddPlayerModal({ onAdd, onClose }) {
  const [name, setName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    onAdd(trimmed)
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">Adicionar Terminal</h2>
        <form onSubmit={handleSubmit}>
          <input
            autoFocus
            className="modal-input"
            type="text"
            placeholder="Nome do jogador"
            maxLength={20}
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn-confirm" disabled={!name.trim()}>
              Adicionar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
