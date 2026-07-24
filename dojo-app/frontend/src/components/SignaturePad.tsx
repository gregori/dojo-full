import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import SignaturePadLib from 'signature_pad'

export interface SignaturePadHandle {
  clear: () => void
  toDataURL: () => string
  isEmpty: () => boolean
}

interface SignaturePadProps {
  width?: number
  height?: number
}

/**
 * A thin, tablet-usable wrapper around the `signature_pad` library: a canvas the
 * operator can draw a signature on, exposing `clear()`/`toDataURL()`/`isEmpty()`
 * via a ref (the library itself handles mouse/touch/pointer events natively).
 */
const SignaturePad = forwardRef<SignaturePadHandle, SignaturePadProps>(function SignaturePad(
  { width = 400, height = 150 },
  ref
) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const padRef = useRef<SignaturePadLib | null>(null)

  useEffect(() => {
    if (!canvasRef.current) return
    padRef.current = new SignaturePadLib(canvasRef.current, {
      backgroundColor: 'rgb(255, 255, 255)',
    })
    return () => {
      padRef.current?.off()
      padRef.current = null
    }
  }, [])

  useImperativeHandle(ref, () => ({
    clear: () => padRef.current?.clear(),
    toDataURL: () => padRef.current?.toDataURL('image/png') || '',
    isEmpty: () => padRef.current?.isEmpty() ?? true,
  }))

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="border border-gray-300 rounded-md bg-white touch-none"
    />
  )
})

export default SignaturePad
