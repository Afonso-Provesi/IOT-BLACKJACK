import axios from 'axios'
import { getDeviceId } from './utils/deviceId'

const BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : '')

const api = axios.create({ baseURL: BASE })

const roomPrefix = (roomId) => (roomId ? `/rooms/${roomId}` : '')

// Attach device identity to every request so the server can enforce ownership
api.interceptors.request.use(config => {
  config.headers['X-Device-ID'] = getDeviceId()
  return config
})

export const getRooms = () => api.get('/rooms').then(r => r.data)

export const createRoom = (name, roomId = undefined) =>
  api.post('/rooms', { name, room_id: roomId }).then(r => r.data)

export const deleteRoom = (roomId) =>
  api.delete(`/rooms/${roomId}`).then(r => r.data)

export const getState = (roomId = undefined) =>
  api.get(`${roomPrefix(roomId)}/game/state`).then(r => r.data)

export const addPlayer = (name, roomId = undefined, player_id = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players`, { name, player_id, owner_token: getDeviceId() }).then(r => r.data)

export const removePlayer = (player_id, roomId = undefined) =>
  api.delete(`${roomPrefix(roomId)}/game/players/${player_id}`).then(r => r.data)

export const placeBet = (player_id, amount, roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players/${player_id}/bet`, { amount }).then(r => r.data)

export const startRound = (roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/start`).then(r => r.data)

export const playerHit = (player_id, roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players/${player_id}/hit`).then(r => r.data)

export const playerStand = (player_id, roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players/${player_id}/stand`).then(r => r.data)

export const playerSplit = (player_id, roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players/${player_id}/split`).then(r => r.data)

export const playerDouble = (player_id, roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/players/${player_id}/double`).then(r => r.data)

export const dealerPlay = (roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/dealer/play`).then(r => r.data)

export const resetGame = (roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/reset`).then(r => r.data)

export const newGame = (roomId = undefined) =>
  api.post(`${roomPrefix(roomId)}/game/new-game`).then(r => r.data)

