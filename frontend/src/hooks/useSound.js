import { useCallback, useRef } from 'react'

// Singleton AudioContext shared across all calls
let _ctx = null
function getCtx() {
  if (!_ctx || _ctx.state === 'closed') {
    _ctx = new (window.AudioContext || window.webkitAudioContext)()
  }
  if (_ctx.state === 'suspended') _ctx.resume()
  return _ctx
}

/**
 * Synthesizes a card-deal sound:
 *   – Whoosh: bandpass-filtered white noise sweeping 1600 Hz → 280 Hz
 *   – Blup:   sine wave dropping 220 Hz → 50 Hz (card landing "thud")
 *
 * @param {number} delay  start offset in seconds (for staggered multi-card deals)
 */
export function playCardDeal(delay = 0) {
  try {
    const ctx = getCtx()
    const t = ctx.currentTime + delay

    // ── Whoosh ────────────────────────────────────────────
    const WHOOSH_DUR = 0.26
    const bufSize = Math.floor(ctx.sampleRate * WHOOSH_DUR)
    const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate)
    const data = buf.getChannelData(0)
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1

    const noiseSrc = ctx.createBufferSource()
    noiseSrc.buffer = buf

    const bpf = ctx.createBiquadFilter()
    bpf.type = 'bandpass'
    bpf.frequency.setValueAtTime(1600, t)
    bpf.frequency.linearRampToValueAtTime(280, t + WHOOSH_DUR)
    bpf.Q.value = 2.2

    const gainW = ctx.createGain()
    gainW.gain.setValueAtTime(0.0, t)
    gainW.gain.linearRampToValueAtTime(0.38, t + 0.03)
    gainW.gain.linearRampToValueAtTime(0.0, t + WHOOSH_DUR)

    noiseSrc.connect(bpf)
    bpf.connect(gainW)
    gainW.connect(ctx.destination)
    noiseSrc.start(t)
    noiseSrc.stop(t + WHOOSH_DUR + 0.05)

    // ── Blup (landing thud) ───────────────────────────────
    const land = t + WHOOSH_DUR - 0.03  // slight overlap with whoosh tail

    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(230, land)
    osc.frequency.exponentialRampToValueAtTime(48, land + 0.11)

    const gainB = ctx.createGain()
    gainB.gain.setValueAtTime(0.65, land)
    gainB.gain.exponentialRampToValueAtTime(0.001, land + 0.14)

    osc.connect(gainB)
    gainB.connect(ctx.destination)
    osc.start(land)
    osc.stop(land + 0.18)
  } catch (e) {
    // AudioContext blocked (e.g. no user interaction yet) — silently skip
  }
}

/**
 * React hook wrapper — keeps a stable reference to playDeal.
 */
export function useCardSound() {
  const play = useCallback((delay = 0) => playCardDeal(delay), [])
  return { playDeal: play }
}
