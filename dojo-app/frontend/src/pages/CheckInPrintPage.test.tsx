import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import CheckInPrintPage from './CheckInPrintPage'
import { buildCheckInUrl } from '../utils/url'

jest.mock('qrcode.react', () => ({
  __esModule: true,
  QRCodeSVG: ({ value }: { value: string }) => <div data-testid="qr-svg" data-value={value} />,
}))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/checkin-print" element={<CheckInPrintPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CheckInPrintPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders the title, QR image, and a print:12cm-sized container when token is present and a title was stored in localStorage', () => {
    localStorage.setItem('checkin-print-title:abc', 'Aula')
    renderAt('/checkin-print?token=abc')

    expect(screen.getByText('Aula')).toBeInTheDocument()
    const qr = screen.getByTestId('qr-svg')
    expect(qr).toHaveAttribute('data-value', buildCheckInUrl('abc'))

    const container = screen.getByRole('img', { name: 'QR code de check-in: Aula' })
    expect(container.className).toContain('print:w-[12cm]')
    expect(container.className).toContain('print:h-[12cm]')

    expect(screen.getByRole('button', { name: 'Imprimir' })).toBeInTheDocument()
  })

  it('falls back to "Check-in" as the title when token is present but no localStorage title is found', () => {
    renderAt('/checkin-print?token=abc')

    expect(screen.getByText('Check-in')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'QR code de check-in: Check-in' })).toBeInTheDocument()
  })

  it('calls window.print() when the Imprimir button is clicked', async () => {
    localStorage.setItem('checkin-print-title:abc', 'Aula')
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {})
    const user = userEvent.setup()
    renderAt('/checkin-print?token=abc')

    await user.click(screen.getByRole('button', { name: 'Imprimir' }))

    expect(printSpy).toHaveBeenCalledTimes(1)
    printSpy.mockRestore()
  })

  it('shows the unavailable message and no QR/print button when token is missing', () => {
    renderAt('/checkin-print')

    expect(screen.getByText('Link de check-in indisponível para este item.')).toBeInTheDocument()
    expect(screen.queryByTestId('qr-svg')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Imprimir' })).not.toBeInTheDocument()
  })
})
