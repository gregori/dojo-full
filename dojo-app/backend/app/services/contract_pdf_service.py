"""Pure PDF rendering for contracts: merge-field validation, context building, and layout.

No DB writes happen here -- this module only turns a template body plus a
data context (and, optionally, a signature image) into PDF bytes.
"""

import io

from fastapi import HTTPException, status
from jinja2 import Template
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from app.models import PlanTier, PlanVersion, Student

REQUIRED_STUDENT_FIELDS = [
    "contract_name",
    "contract_cpf",
    "address_street",
    "address_neighborhood",
    "address_city",
    "address_zip",
    "birth_date",
    "phone",
]


class ContractPdfService:
    """Render contract PDFs from a template body and student/plan data (D3, CON-02)."""

    @staticmethod
    def validate_merge_fields(student: Student) -> None:
        """Raise, naming every missing field, unless all required legal-data fields are populated."""
        missing = [field for field in REQUIRED_STUDENT_FIELDS if not getattr(student, field, None)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required student data: {', '.join(missing)}",
            )

    @staticmethod
    def build_context(student: Student, plan_tier: PlanTier, plan_version: PlanVersion) -> dict:
        """Pre-format student/plan/plan-version data into display strings for template substitution."""
        address = (
            f"{student.address_street}, {student.address_neighborhood}, {student.address_city} - {student.address_zip}"
        )
        return {
            "student": {
                "contract_name": student.contract_name,
                "contract_cpf": student.contract_cpf,
                "address": address,
                "birth_date": student.birth_date.strftime("%d/%m/%Y") if student.birth_date else "",
                "phone": student.phone,
            },
            "plan_tier": {
                "name": plan_tier.name,
                "weekly_frequency": plan_tier.weekly_frequency,
            },
            "plan_version": {
                "price": f"R$ {plan_version.price:,.2f}",
            },
        }

    @staticmethod
    def render_pdf(template_body: str, context: dict, signature_png: bytes | None = None) -> bytes:
        """Render the merged template body (paragraph breaks on blank lines) into PDF bytes."""
        rendered = Template(template_body).render(**context)

        styles = getSampleStyleSheet()
        story = []
        for paragraph_text in rendered.split("\n\n"):
            paragraph_text = paragraph_text.strip()
            if not paragraph_text:
                continue
            story.append(Paragraph(paragraph_text.replace("\n", "<br/>"), styles["Normal"]))
            story.append(Spacer(1, 12))

        if signature_png is not None:
            story.append(Spacer(1, 24))
            story.append(Image(io.BytesIO(signature_png), width=200, height=80))
            story.append(Paragraph("Assinatura", styles["Normal"]))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build(story)
        return buffer.getvalue()
