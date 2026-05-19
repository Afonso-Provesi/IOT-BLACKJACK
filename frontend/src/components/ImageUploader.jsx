import { useState, useRef } from 'react'
import { uploadImage } from '../api'
import { Upload, Loader2 } from 'lucide-react'

export default function ImageUploader({ onResult }) {
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()

  const handleFile = async (file) => {
    if (!file) return
    setError(null)

    // Preview local
    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target.result)
    reader.readAsDataURL(file)

    setLoading(true)
    try {
      const res = await uploadImage(file)
      onResult(res.data)
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.message
      setError(`Erro: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  return (
    <div className="space-y-3">
      <div
        className="border-2 border-dashed border-green-600 rounded-xl p-6 flex flex-col items-center justify-center gap-3 cursor-pointer hover:bg-green-900/20 transition"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
      >
        {loading ? (
          <Loader2 className="animate-spin w-8 h-8 text-green-400" />
        ) : (
          <Upload className="w-8 h-8 text-green-400" />
        )}
        <p className="text-sm text-gray-300">
          {loading ? 'Processando...' : 'Clique ou arraste uma imagem de carta'}
        </p>
        <p className="text-xs text-gray-500">JPEG, PNG, WEBP</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {preview && (
        <div className="flex justify-center">
          <img
            src={preview}
            alt="Preview"
            className="max-h-48 rounded-lg border border-gray-600 object-contain shadow"
          />
        </div>
      )}

      {error && (
        <div className="bg-red-900/40 border border-red-600 rounded-lg p-2 text-red-300 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}
