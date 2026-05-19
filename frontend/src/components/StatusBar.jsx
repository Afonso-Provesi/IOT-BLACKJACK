export default function StatusBar({ mqttConnected, wsConnected }) {
  return (
    <div className="flex items-center gap-4 text-xs">
      <div className="flex items-center gap-1.5">
        <span className={`pulse-dot ${mqttConnected ? 'bg-green-400' : 'bg-red-500'}`} />
        <span className="text-gray-300">MQTT</span>
        <span className={mqttConnected ? 'text-green-400' : 'text-red-400'}>
          {mqttConnected ? 'Online' : 'Offline'}
        </span>
      </div>
      <div className="h-3 w-px bg-white/20" />
      <div className="flex items-center gap-1.5">
        <span className={`pulse-dot ${wsConnected ? 'bg-blue-400' : 'bg-yellow-500'}`} />
        <span className="text-gray-300">WebSocket</span>
        <span className={wsConnected ? 'text-blue-400' : 'text-yellow-400'}>
          {wsConnected ? 'Conectado' : 'Reconectando...'}
        </span>
      </div>
    </div>
  )
}
