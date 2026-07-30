import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import QrCodeModal from './QrCodeModal'
import { buildCheckInUrl, buildCheckInPrintUrl } from '../utils/url'

jest.mock('qrcode.react', () => ({
  __esModule: true,
  QRCodeSVG: ({ value }: { value: string }) => <div data-testid="qr-svg" data-value={value} />,
}))

describe('QrCodeModal', () => {
  it('renders the title and a QR element encoding buildCheckInUrl(token)', () => {
    render(<QrCodeModal title="Aula de Judo" token="tok-123" onClose={jest.fn()} />)

    expect(screen.getByText('Aula de Judo')).toBeInTheDocument()
    expect(screen.getByTestId('qr-svg')).toHaveAttribute('data-value', buildCheckInUrl('tok-123'))
  })

  it('renders a print link pointing to buildCheckInPrintUrl(token), opening in a new tab', () => {
    render(<QrCodeModal title="Aula de Judo" token="tok-123" onClose={jest.fn()} />)

    const printLink = screen.getByRole('link', { name: 'Imprimir' })
    expect(printLink).toHaveAttribute('href', buildCheckInPrintUrl('tok-123'))
    expect(printLink).toHaveAttribute('target', '_blank')
    expect(printLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('stores the title in localStorage keyed by token when the print link is clicked', async () => {
    const user = userEvent.setup()
    render(<QrCodeModal title="Aula de Judo" token="tok-123" onClose={jest.fn()} />)

    const printLink = screen.getByRole('link', { name: 'Imprimir' })
    await user.click(printLink)

    expect(localStorage.getItem('checkin-print-title:tok-123')).toBe('Aula de Judo')
  })

  it('calls onClose when the close button is clicked', async () => {
    const onClose = jest.fn()
    const user = userEvent.setup()
    render(<QrCodeModal title="Aula de Judo" token="tok-123" onClose={onClose} />)

    await user.click(screen.getByRole('button', { name: 'Fechar' }))

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it.each<[string | null, string]>([
    ['', 'empty string'],
    [null, 'null'],
  ])(
    'with a falsy token (%s: %s), shows the unavailable message and no QR/print link, without throwing',
    (token) => {
      render(<QrCodeModal title="Aula de Judo" token={token} onClose={jest.fn()} />)

      expect(screen.getByText('Link de check-in indisponível para este item.')).toBeInTheDocument()
      expect(screen.queryByTestId('qr-svg')).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Imprimir' })).not.toBeInTheDocument()
    }
  )
})
