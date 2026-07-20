import { useState } from 'react'
import { CheckCircle2, CircleAlert, LoaderCircle, Stethoscope } from 'lucide-react'
import { publicApi } from '../services/api'

interface MedicalExamPublicResponse {
  message?: string
}

export default function MedicalExamPage() {
  const [registrationNumber, setRegistrationNumber] = useState('')
  const [pin, setPin] = useState('')
  const [examDate, setExamDate] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(
    null
  )

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFeedback(null)

    if (!file) {
      setFeedback({ kind: 'error', message: 'Selecione o arquivo do exame (PDF, JPEG ou PNG).' })
      return
    }

    setSubmitting(true)
    try {
      const body = new FormData()
      body.append('registration_number', registrationNumber.trim())
      body.append('pin', pin)
      body.append('exam_date', examDate)
      body.append('file', file)

      // publicApi defaults to Content-Type: application/json, which would make axios
      // serialize this FormData as JSON instead of a real multipart body. Clearing the
      // header (rather than setting a static string) lets axios/the browser compute the
      // correct `multipart/form-data; boundary=...` value itself.
      const response = await publicApi.post<MedicalExamPublicResponse>(
        '/api/v1/medical-exams/public/submit',
        body,
        { headers: { 'Content-Type': undefined } }
      )
      setFeedback({
        kind: 'success',
        message:
          response.data.message ||
          'Se os dados informados forem válidos, seu exame foi registrado com sucesso.',
      })
      setPin('')
      setExamDate('')
      setFile(null)
    } catch {
      setFeedback({
        kind: 'error',
        message:
          'Não foi possível concluir esta solicitação. Confira os dados informados e tente novamente.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 sm:px-6">
      <section className="mx-auto max-w-xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/30">
        <header className="border-b border-slate-700 bg-slate-900 px-6 py-8 sm:px-10">
          <p className="mb-2 text-xs font-bold tracking-[0.24em] text-cyan-300 uppercase">
            Dojo Admin
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Exame Médico</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Envie a data e o comprovante do seu exame médico. O documento é armazenado com segurança
            e usado apenas para controle interno.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-6 px-6 py-8 sm:px-10">
          {feedback && (
            <div
              role="status"
              className={`flex gap-3 rounded-lg border p-4 text-sm leading-5 ${
                feedback.kind === 'success'
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
                  : 'border-rose-500/40 bg-rose-500/10 text-rose-100'
              }`}
            >
              {feedback.kind === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              ) : (
                <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          <div className="grid gap-5 sm:grid-cols-[1fr_9rem]">
            <div>
              <label
                htmlFor="registration"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Matrícula
              </label>
              <input
                id="registration"
                value={registrationNumber}
                onChange={(event) => setRegistrationNumber(event.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                placeholder="Ex.: 2024001"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label htmlFor="pin" className="mb-2 block text-sm font-medium text-slate-200">
                PIN
              </label>
              <input
                id="pin"
                type="password"
                value={pin}
                onChange={(event) => setPin(event.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                inputMode="numeric"
                maxLength={4}
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="exam-date" className="mb-2 block text-sm font-medium text-slate-200">
              Data do Exame
            </label>
            <input
              id="exam-date"
              type="date"
              value={examDate}
              onChange={(event) => setExamDate(event.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
              required
            />
          </div>

          <div>
            <label htmlFor="exam-file" className="mb-2 block text-sm font-medium text-slate-200">
              Comprovante (PDF, JPEG ou PNG, até 10MB)
            </label>
            <input
              id="exam-file"
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-3 text-sm text-slate-200 outline-none transition file:mr-3 file:rounded-md file:border-0 file:bg-cyan-400 file:px-3 file:py-1.5 file:text-slate-950 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 font-bold text-slate-950 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {submitting ? (
              <LoaderCircle className="h-5 w-5 animate-spin" />
            ) : (
              <Stethoscope className="h-5 w-5" />
            )}
            {submitting ? 'Enviando...' : 'Enviar exame'}
          </button>
        </form>
      </section>
    </main>
  )
}
