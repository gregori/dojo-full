import { QRCodeSVG } from 'qrcode.react'

interface QrImageProps {
  value: string
  title: string
  size: number
  className?: string
}

export default function QrImage({ value, title, size, className }: QrImageProps) {
  return (
    <div role="img" aria-label={`QR code de check-in: ${title}`} className={className}>
      <QRCodeSVG value={value} size={size} className="h-full w-full" />
    </div>
  )
}
