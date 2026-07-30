import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import QrImage from '../components/QrImage'
import { buildCheckInUrl } from '../utils/url'

export default function CheckInPrintPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const hasToken = Boolean(token)
  const [title] = useState(() => {
    if (!token) return ''
    const key = `checkin-print-title:${token}`
    const stored = localStorage.getItem(key)
    localStorage.removeItem(key)
    return stored ?? 'Check-in'
  })

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-white p-8 print:p-0">
      {hasToken ? (
        <>
          <h1 className="text-center text-2xl font-bold text-gray-900">{title}</h1>
          <QrImage
            value={buildCheckInUrl(token as string)}
            title={title}
            size={300}
            className="flex h-[300px] w-[300px] items-center justify-center print:h-[12cm] print:w-[12cm]"
          />
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 print:hidden"
          >
            Imprimir
          </button>
        </>
      ) : (
        <p className="text-center text-rose-700">
          Link de check-in indisponível para este item.
        </p>
      )}
    </main>
  )
}
