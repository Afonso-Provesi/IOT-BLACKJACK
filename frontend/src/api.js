import axios from 'axios'

const BASE = 'http://localhost:8001'

const api = axios.create({ baseURL: BASE })

export const getState = () => api.get('/game/state').then(r => r.data)

export const addPlayer = (name, player_id = undefined) =>
  api.post('/game/players', { name, player_id }).then(r => r.data)

export const removePlayer = (player_id) =>
  api.delete(`/game/players/${player_id}`).then(r => r.data)

export const placeBet = (player_id, amount) =>
  api.post(`/game/players/${player_id}/bet`, { amount }).then(r => r.data)

export const startRound = () =>
  api.post('/game/start').then(r => r.data)

export const playerHit = (player_id) =>
  api.post(`/game/players/${player_id}/hit`).then(r => r.data)

export const playerStand = (player_id) =>
  api.post(`/game/players/${player_id}/stand`).then(r => r.data)

export const playerSplit = (player_id) =>
  api.post(`/game/players/${player_id}/split`).then(r => r.data)

export const playerDouble = (player_id) =>
  api.post(`/game/players/${player_id}/double`).then(r => r.data)

export const dealerPlay = () =>
  api.post('/game/dealer/play').then(r => r.data)

export const resetGame = () =>
  api.post('/game/reset').then(r => r.data)

export const newGame = () =>
  api.post('/game/new-game').then(r => r.data)

