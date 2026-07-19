/* eslint-disable react-refresh/only-export-components -- toast singleton pattern */
import { useState, useEffect } from 'react'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
}

let toastListeners: ((toasts: Toast[]) => void)[] = []
let toasts: Toast[] = []

export function showToast(message: string, type: Toast['type'] = 'info') {
  const toast: Toast = {
    id: Date.now().toString(),
    message,
    type,
  }
  toasts = [...toasts, toast]
  toastListeners.forEach((listener) => listener(toasts))

  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== toast.id)
    toastListeners.forEach((listener) => listener(toasts))
  }, 3000)
}

export function ToastContainer() {
  const [toastList, setToastList] = useState<Toast[]>([])

  useEffect(() => {
    toastListeners.push(setToastList)
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setToastList)
    }
  }, [])

  const getIcon = (type: Toast['type']) => {
    switch (type) {
      case 'success':
        return '✓'
      case 'error':
        return '✗'
      case 'warning':
        return '⚠'
      default:
        return 'ℹ'
    }
  }

  const getColors = (type: Toast['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800'
    }
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toastList.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center px-4 py-3 rounded-lg border shadow-lg transition-all ${getColors(
            toast.type
          )}`}
        >
          <span className="mr-2 text-lg">{getIcon(toast.type)}</span>
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      ))}
    </div>
  )
}
