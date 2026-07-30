export function toAbsoluteUrl(pathWithQuery: string): string {
  return `${window.location.origin}${pathWithQuery}`
}

export function buildCheckInUrl(token: string): string {
  return toAbsoluteUrl(`/checkin?token=${encodeURIComponent(token)}`)
}

export function buildCheckInPrintUrl(token: string): string {
  return toAbsoluteUrl(`/checkin-print?token=${encodeURIComponent(token)}`)
}

export function buildPreCheckInUrl(eventId?: string): string {
  return eventId
    ? toAbsoluteUrl(`/precheckin?event_id=${encodeURIComponent(eventId)}`)
    : toAbsoluteUrl('/precheckin')
}
