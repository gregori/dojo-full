import { copyToClipboardWithToast } from './clipboard'
import { showToast } from '../components/Toast'

jest.mock('../components/Toast', () => ({
  __esModule: true,
  showToast: jest.fn(),
}))

const mockedShowToast = showToast as jest.Mock

describe('copyToClipboardWithToast', () => {
  beforeEach(() => {
    mockedShowToast.mockReset()
  })

  it('shows a success toast when navigator.clipboard.writeText resolves', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: jest.fn().mockResolvedValue(undefined) },
    })

    await copyToClipboardWithToast('https://app.example.com/precheckin')

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      'https://app.example.com/precheckin'
    )
    expect(mockedShowToast).toHaveBeenCalledWith('Link copiado', 'success')
  })

  it('shows an error toast and never rejects when navigator.clipboard.writeText rejects', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: jest.fn().mockRejectedValue(new Error('denied')) },
    })

    await expect(copyToClipboardWithToast('https://app.example.com/precheckin')).resolves.toBeUndefined()

    expect(mockedShowToast).toHaveBeenCalledWith('Não foi possível copiar o link', 'error')
  })
})
