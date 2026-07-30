import { showToast } from '../components/Toast'

export async function copyToClipboardWithToast(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    showToast('Link copiado', 'success')
  } catch {
    showToast('Não foi possível copiar o link', 'error')
  }
}
