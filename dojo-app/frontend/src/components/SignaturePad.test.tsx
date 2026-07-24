import { createRef } from 'react'
import { render } from '@testing-library/react'
import SignaturePad, { type SignaturePadHandle } from './SignaturePad'

// jsdom doesn't implement a real canvas rendering context; signature_pad only
// needs a handful of drawing primitives at construction/clear() time, and its
// own toDataURL() delegates straight to the canvas element's toDataURL().
beforeEach(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
    fillStyle: '',
    clearRect: jest.fn(),
    fillRect: jest.fn(),
  })) as unknown as typeof HTMLCanvasElement.prototype.getContext
  HTMLCanvasElement.prototype.toDataURL = jest.fn(() => 'data:image/png;base64,fakedata')
})

describe('SignaturePad', () => {
  it('mounts a canvas', () => {
    const ref = createRef<SignaturePadHandle>()
    const { container } = render(<SignaturePad ref={ref} />)

    expect(container.querySelector('canvas')).toBeInTheDocument()
  })

  it('reports isEmpty() as true before any drawing', () => {
    const ref = createRef<SignaturePadHandle>()
    render(<SignaturePad ref={ref} />)

    expect(ref.current?.isEmpty()).toBe(true)
  })

  it('toDataURL() returns a PNG data URL', () => {
    const ref = createRef<SignaturePadHandle>()
    render(<SignaturePad ref={ref} />)

    expect(ref.current?.toDataURL()).toBe('data:image/png;base64,fakedata')
  })

  it('clear() does not throw', () => {
    const ref = createRef<SignaturePadHandle>()
    render(<SignaturePad ref={ref} />)

    expect(() => ref.current?.clear()).not.toThrow()
  })
})
