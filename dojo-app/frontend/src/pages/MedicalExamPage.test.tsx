import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MedicalExamPage from './MedicalExamPage'
import { publicApi } from '../services/api'

jest.mock('../services/api', () => ({
  publicApi: { post: jest.fn() },
}))

const mockedPost = publicApi.post as jest.Mock

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Matrícula'), '123456')
  await user.type(screen.getByLabelText('PIN'), '1234')
  await user.type(screen.getByLabelText('Data do Exame'), '2026-01-15')
}

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await fillRequiredFields(user)
  const file = new File(['%PDF-1.4'], 'exam.pdf', { type: 'application/pdf' })
  await user.upload(screen.getByLabelText(/Comprovante/), file)
  // jsdom's file-input constraint validation doesn't understand MIME-type
  // `accept` values (only extension-based ones), so it always reports this
  // (correctly-filled) input as invalid and a real button click never
  // submits. Dispatching `submit` directly bypasses that native-validation
  // gate, same as it would pass in a real browser. Wrapped in `act` so the
  // handler's own async state updates settle before we assert.
  const form = screen.getByRole('button', { name: /Enviar exame/i }).closest('form')!
  await act(async () => {
    fireEvent.submit(form)
  })
}

describe('MedicalExamPage', () => {
  beforeEach(() => {
    mockedPost.mockReset()
  })

  it('shows the fixed Portuguese success message on success, regardless of the response body', async () => {
    // The backend intentionally always returns the same generic (English) message, whatever
    // the outcome, so the frontend must not surface it verbatim as its own success message.
    mockedPost.mockResolvedValueOnce({
      data: {
        status: 'accepted',
        message: 'If the supplied details are valid, your request has been processed.',
      },
    })
    const user = userEvent.setup()
    render(<MedicalExamPage />)

    await fillAndSubmit(user)

    expect(await screen.findByText(/seu exame foi registrado com sucesso/i)).toBeInTheDocument()
    expect(screen.queryByText(/supplied details are valid/i)).not.toBeInTheDocument()
  })

  it('sends the file as multipart form data with an auto-computed Content-Type', async () => {
    mockedPost.mockResolvedValueOnce({ data: { status: 'accepted', message: 'ok' } })
    const user = userEvent.setup()
    render(<MedicalExamPage />)

    await fillAndSubmit(user)

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1))
    const [url, body, config] = mockedPost.mock.calls[0]
    expect(url).toBe('/api/v1/medical-exams/public/submit')
    expect(body).toBeInstanceOf(FormData)
    expect(config.headers['Content-Type']).toBeUndefined()
  })

  it('shows a generic error message when the request fails', async () => {
    mockedPost.mockRejectedValueOnce(new Error('network error'))
    const user = userEvent.setup()
    render(<MedicalExamPage />)

    await fillAndSubmit(user)

    expect(
      await screen.findByText(/não foi possível concluir esta solicitação/i)
    ).toBeInTheDocument()
  })

  it('does not submit when no file is selected', async () => {
    const user = userEvent.setup()
    render(<MedicalExamPage />)

    // The file input is itself marked `required`, so the browser's (and jsdom's)
    // native constraint validation blocks submission before our onSubmit handler
    // ever runs -- there's no user-visible message to assert on here.
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: /Enviar exame/i }))

    expect(mockedPost).not.toHaveBeenCalled()
  })
})
