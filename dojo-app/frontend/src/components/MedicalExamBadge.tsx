export type MedicalExamStatusValue = 'valido' | 'vencendo' | 'vencido' | 'sem_registro'

const MEDICAL_EXAM_BADGE: Record<MedicalExamStatusValue, { label: string; className: string }> = {
  valido: { label: 'Válido', className: 'bg-green-100 text-green-800' },
  vencendo: { label: 'Vencendo', className: 'bg-yellow-100 text-yellow-800' },
  vencido: { label: 'Vencido', className: 'bg-red-100 text-red-800' },
  sem_registro: { label: 'Sem registro', className: 'bg-gray-100 text-gray-600' },
}

/** Renders the computed medical-exam status as a colored pill, or a loading placeholder. */
export default function MedicalExamBadge({
  status,
}: {
  status: MedicalExamStatusValue | undefined
}) {
  const badge = status ? MEDICAL_EXAM_BADGE[status] : null
  if (!badge) {
    return <span className="text-xs text-gray-400">Carregando...</span>
  }
  return (
    <span
      className={`inline-flex px-2 text-xs leading-5 font-semibold rounded-full ${badge.className}`}
    >
      {badge.label}
    </span>
  )
}
