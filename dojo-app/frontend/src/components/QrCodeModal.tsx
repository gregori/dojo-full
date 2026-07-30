import { X } from 'lucide-react'
import QrImage from './QrImage'
import { buildCheckInUrl, buildCheckInPrintUrl } from '../utils/url'

interface QrCodeModalProps {
  title: string
  token: string | null | undefined
  onClose: () => void
}

export default function QrCodeModal({ title, token, onClose }: QrCodeModalProps) {
  const hasToken = Boolean(token)

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="rounded p-1 text-slate-500 hover:bg-gray-100 hover:text-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {hasToken ? (
          <>
            <QrImage
              value={buildCheckInUrl(token as string)}
              title={title}
              size={240}
              className="flex justify-center py-4"
            />
            <a
              href={buildCheckInPrintUrl(token as string)}
              onClick={() => localStorage.setItem(`checkin-print-title:${token}`, title)}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Imprimir
            </a>
          </>
        ) : (
          <p className="py-4 text-sm text-rose-700">
            Link de check-in indisponível para este item.
          </p>
        )}
      </div>
    </div>
  )
}
