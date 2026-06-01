import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { CheckCircle, XCircle, Loader } from 'lucide-react'

export default function CheckInPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [registrationNumber, setRegistrationNumber] = useState('')
  const [pin, setPin] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  // Kiosk mode detection
  const isKioskMode = !token

  useEffect(() => {
    // Auto-focus registration input
    if (isKioskMode) {
      document.getElementById('registration')?.focus()
    }
  }, [isKioskMode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      let response
      if (token) {
        // QR Code check-in
        response = await api.post('/api/v1/checkin/qr', {
          registration_number: registrationNumber,
          pin,
          check_in_token: token,
        })
      } else {
        // Tablet check-in - requires event_id
        // For now, we'll show an error or redirect
        setError('Modo tablet requer seleção de evento. Use o link do evento.')
        setLoading(false)
        return
      }

      setResult(response.data)

      // Clear form after 5 seconds
      setTimeout(() => {
        setRegistrationNumber('')
        setPin('')
        setResult(null)
        document.getElementById('registration')?.focus()
      }, 5000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao registrar presença')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className={`min-h-screen flex items-center justify-center ${
        isKioskMode ? 'bg-gray-900' : 'bg-gray-100'
      }`}
    >
      <div
        className={`w-full max-w-md p-8 rounded-lg shadow-lg ${
          isKioskMode ? 'bg-gray-800 text-white' : 'bg-white'
        }`}
      >
        <div className="text-center mb-8">
          <h1 className={`text-3xl font-bold ${isKioskMode ? 'text-white' : 'text-gray-800'}`}>
            {token ? 'Check-in QR Code' : 'Check-in'}
          </h1>
          <p className={`mt-2 ${isKioskMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {token
              ? 'Digite sua matrícula e PIN para confirmar presença'
              : 'Digite sua matrícula e PIN'}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg mb-6 flex items-center">
            <XCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        )}

        {result && (
          <div className="bg-green-50 border border-green-200 text-green-800 p-6 rounded-lg mb-6">
            <div className="flex items-center mb-2">
              <CheckCircle className="w-6 h-6 mr-2" />
              <span className="font-semibold text-lg">{result.message}</span>
            </div>
            {result.progress && (
              <div className="mt-4 space-y-2">
                <p className="text-sm">
                  <span className="font-medium">Faixa atual:</span> {result.progress.current_belt}
                </p>
                {result.progress.next_belt && (
                  <>
                    <p className="text-sm">
                      <span className="font-medium">Próxima faixa:</span>{' '}
                      {result.progress.next_belt}
                    </p>
                    <div className="mt-3">
                      <p className="text-sm font-medium mb-2">Progresso:</p>
                      {result.progress.requirements?.map((req: any, index: number) => (
                        <div key={index} className="flex justify-between text-sm mb-1">
                          <span>{req.description}:</span>
                          <span className={req.is_complete ? 'text-green-600' : 'text-orange-600'}>
                            {req.completed}/{req.required}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {result.progress.message && (
                  <p className="text-sm font-medium text-blue-600 mt-2">
                    {result.progress.message}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              className={`block text-sm font-medium mb-1 ${
                isKioskMode ? 'text-gray-200' : 'text-gray-700'
              }`}
            >
              Matrícula
            </label>
            <input
              id="registration"
              type="text"
              value={registrationNumber}
              onChange={(e) => setRegistrationNumber(e.target.value)}
              className={`w-full px-4 py-3 text-lg rounded-lg border-2 focus:outline-none focus:ring-2 ${
                isKioskMode
                  ? 'bg-gray-700 border-gray-600 text-white focus:ring-blue-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
              placeholder="Ex: 2024001"
              required
              autoFocus
            />
          </div>

          <div>
            <label
              className={`block text-sm font-medium mb-1 ${
                isKioskMode ? 'text-gray-200' : 'text-gray-700'
              }`}
            >
              PIN
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className={`w-full px-4 py-3 text-lg rounded-lg border-2 focus:outline-none focus:ring-2 ${
                isKioskMode
                  ? 'bg-gray-700 border-gray-600 text-white focus:ring-blue-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
              placeholder="4 dígitos"
              maxLength={4}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-4 text-lg font-semibold rounded-lg transition-colors flex items-center justify-center ${
              isKioskMode
                ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-600'
                : 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-400'
            }`}
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 mr-2 animate-spin" />
                Processando...
              </>
            ) : (
              'Confirmar Presença'
            )}
          </button>
        </form>

        {isKioskMode && (
          <div className="mt-8 text-center text-gray-400 text-sm">
            <p>Sistema de Gestão de Dojo</p>
          </div>
        )}
      </div>
    </div>
  )
}
