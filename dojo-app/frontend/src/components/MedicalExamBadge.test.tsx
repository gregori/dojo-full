import { render, screen } from '@testing-library/react'
import MedicalExamBadge from './MedicalExamBadge'

describe('MedicalExamBadge', () => {
  it('renders a loading placeholder when status is undefined', () => {
    render(<MedicalExamBadge status={undefined} />)
    expect(screen.getByText('Carregando...')).toBeInTheDocument()
  })

  it.each([
    ['valido', 'Válido'],
    ['vencendo', 'Vencendo'],
    ['vencido', 'Vencido'],
    ['sem_registro', 'Sem registro'],
  ] as const)('renders the %s label for status %s', (status, label) => {
    render(<MedicalExamBadge status={status} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })
})
