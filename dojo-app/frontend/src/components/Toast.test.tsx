import { render, screen, act } from '@testing-library/react'
import { ToastContainer, showToast } from './Toast'

describe('Toast', () => {
  beforeEach(() => {
    jest.useFakeTimers()
  })

  afterEach(() => {
    // Drain any pending auto-dismiss timers before restoring real timers, so
    // they don't fire (and warn about updates outside act()) in a later test.
    act(() => {
      jest.runOnlyPendingTimers()
    })
    jest.useRealTimers()
  })

  it('renders nothing when no toast has been shown', () => {
    const { container } = render(<ToastContainer />)
    expect(container.textContent).toBe('')
  })

  it('shows a toast message when showToast() is called', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Saved successfully', 'success')
    })

    expect(screen.getByText('Saved successfully')).toBeInTheDocument()
  })

  it('auto-dismisses a toast after 3 seconds', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Temporary message')
    })
    expect(screen.getByText('Temporary message')).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(3000)
    })

    expect(screen.queryByText('Temporary message')).not.toBeInTheDocument()
  })
})
