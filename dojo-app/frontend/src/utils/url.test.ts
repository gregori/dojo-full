import { toAbsoluteUrl, buildCheckInUrl, buildCheckInPrintUrl, buildPreCheckInUrl } from './url'

describe('url utils', () => {
  const origin = window.location.origin

  it('toAbsoluteUrl prefixes the path with window.location.origin only', () => {
    expect(toAbsoluteUrl('/foo?bar=baz')).toBe(`${origin}/foo?bar=baz`)
  })

  it('buildCheckInUrl returns an absolute, URL-encoded check-in link', () => {
    expect(buildCheckInUrl('token abc/123')).toBe(`${origin}/checkin?token=token%20abc%2F123`)
  })

  it('buildCheckInPrintUrl returns an absolute, URL-encoded print link with the token', () => {
    expect(buildCheckInPrintUrl('tok en')).toBe(`${origin}/checkin-print?token=tok%20en`)
  })

  it('buildPreCheckInUrl() with no argument returns the bare absolute /precheckin URL', () => {
    expect(buildPreCheckInUrl()).toBe(`${origin}/precheckin`)
  })

  it('buildPreCheckInUrl(eventId) returns the absolute /precheckin URL with event_id', () => {
    expect(buildPreCheckInUrl('event-1')).toBe(`${origin}/precheckin?event_id=event-1`)
  })
})
