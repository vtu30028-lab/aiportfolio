"""
PortfolioAI - Server-Side Portfolio PDF Generation Engine
Generates publication-quality, ATS-friendly developer portfolio PDFs using ReportLab.
Includes clickable links, custom theme accents, structured sections, and multi-page flows.
"""

import io
import re
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class PDFGenerationError(Exception):
    """Raised when PDF generation encounters an irrecoverable error."""
    pass


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page count
    and render consistent running headers and footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 36, letter[0] - 36, 36)

        # Footer text
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 24, footer_text)
        self.drawString(36, 24, "Created with PortfolioAI — AI-Powered Developer Portfolio Generator")
        self.restoreState()


class PortfolioPDFGenerator:
    """Generates styled, multi-section developer portfolio PDFs."""

    @classmethod
    def generate(cls, portfolio) -> io.BytesIO:
        """
        Builds a complete PDF for the given Portfolio entity.
        Returns a BytesIO buffer positioned at offset 0.
        """
        buffer = io.BytesIO()

        # Parse accent color safely
        accent_hex = portfolio.accent_color or "#6366f1"
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", accent_hex):
            accent_hex = "#6366f1"
        accent_color = colors.HexColor(accent_hex)
        dark_text = colors.HexColor("#0f172a")
        muted_text = colors.HexColor("#475569")

        # Document setup: 0.5 inch (36 pt) margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=40,
            bottomMargin=50,
        )

        styles = getSampleStyleSheet()

        # Typography Styles
        name_style = ParagraphStyle(
            "PortfolioName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=accent_color,
            spaceAfter=3,
        )

        headline_style = ParagraphStyle(
            "PortfolioHeadline",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=dark_text,
            spaceAfter=6,
        )

        contact_style = ParagraphStyle(
            "PortfolioContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=muted_text,
            spaceAfter=12,
        )

        section_heading_style = ParagraphStyle(
            "PortfolioSectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=dark_text,
            spaceBefore=14,
            spaceAfter=4,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "PortfolioBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=dark_text,
            spaceAfter=6,
        )

        item_title_style = ParagraphStyle(
            "PortfolioItemTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=dark_text,
        )

        item_subtitle_style = ParagraphStyle(
            "PortfolioItemSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=accent_color,
        )

        item_meta_style = ParagraphStyle(
            "PortfolioItemMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=muted_text,
            alignment=2,  # Right-aligned
        )

        story = []

        # =================================================================
        # 1. Header: Name, Headline, Contact details
        # =================================================================
        full_name = xml_escape(portfolio.full_name or "Developer Portfolio")
        headline = xml_escape(portfolio.headline or "Software Engineer")

        story.append(Paragraph(full_name, name_style))
        story.append(Paragraph(headline, headline_style))

        # Contact line with clickable links
        contact_parts = []
        if portfolio.email:
            email_esc = xml_escape(portfolio.email)
            contact_parts.append(f'<link href="mailto:{email_esc}">{email_esc}</link>')
        if portfolio.phone:
            contact_parts.append(xml_escape(portfolio.phone))
        if portfolio.location:
            contact_parts.append(xml_escape(portfolio.location))
        if portfolio.github_url:
            gh_esc = xml_escape(portfolio.github_url)
            contact_parts.append(f'<link href="{gh_esc}">GitHub</link>')
        if portfolio.linkedin_url:
            li_esc = xml_escape(portfolio.linkedin_url)
            contact_parts.append(f'<link href="{li_esc}">LinkedIn</link>')
        if portfolio.is_published:
            pub_url = xml_escape(portfolio.get_public_url())
            contact_parts.append(f'<link href="{pub_url}">Live Portfolio</link>')

        if contact_parts:
            story.append(Paragraph(" • ".join(contact_parts), contact_style))

        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=0, spaceAfter=8))

        # =================================================================
        # 2. About Me Section
        # =================================================================
        if portfolio.about and portfolio.about.strip():
            story.append(Paragraph("ABOUT ME", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))
            about_text = xml_escape(portfolio.about.strip()).replace("\n", "<br/>")
            story.append(Paragraph(about_text, body_style))
            story.append(Spacer(1, 6))

        # =================================================================
        # 3. Technical Skills Section
        # =================================================================
        skills_list = portfolio.get_skills_list()
        if skills_list:
            story.append(Paragraph("TECHNICAL & PROFESSIONAL SKILLS", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))
            skills_str = " • ".join([xml_escape(s) for s in skills_list])
            story.append(Paragraph(skills_str, body_style))
            story.append(Spacer(1, 6))

        # =================================================================
        # 4. Featured Projects Section
        # =================================================================
        if portfolio.projects:
            story.append(Paragraph("FEATURED ENGINEERING PROJECTS", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))

            for proj in portfolio.projects:
                proj_elements = []
                title_esc = xml_escape(proj.title)

                # Project title row: Left = Title & Tech, Right = Code / Demo links
                links = []
                if proj.github_url:
                    gh_esc = xml_escape(proj.github_url)
                    links.append(f'<link href="{gh_esc}">Source Code</link>')
                if proj.live_url:
                    live_esc = xml_escape(proj.live_url)
                    links.append(f'<link href="{live_esc}">Live Demo</link>')

                links_html = " • ".join(links) if links else ""

                header_table = Table(
                    [
                        [
                            Paragraph(title_esc, item_title_style),
                            Paragraph(links_html, item_meta_style),
                        ]
                    ],
                    colWidths=[360, 180],
                )
                header_table.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ])
                )
                proj_elements.append(header_table)

                if proj.technologies:
                    tech_esc = xml_escape(proj.technologies)
                    proj_elements.append(Paragraph(f"<b>Tech Stack:</b> {tech_esc}", item_subtitle_style))

                if proj.description:
                    desc_esc = xml_escape(proj.description).replace("\n", "<br/>")
                    proj_elements.append(Paragraph(desc_esc, body_style))

                proj_elements.append(Spacer(1, 4))
                story.append(KeepTogether(proj_elements))

            story.append(Spacer(1, 4))

        # =================================================================
        # 5. Professional Work Experience
        # =================================================================
        experience_list = portfolio.get_experience_list()
        if experience_list:
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))

            for exp in experience_list:
                exp_elements = []
                role = xml_escape(exp.get("role") or exp.get("title") or "Software Engineer")
                company = xml_escape(exp.get("company") or exp.get("organization") or "")
                duration = xml_escape(exp.get("duration") or exp.get("dates") or "")

                row_table = Table(
                    [
                        [
                            Paragraph(f"<b>{role}</b> — {company}" if company else f"<b>{role}</b>", item_title_style),
                            Paragraph(duration, item_meta_style),
                        ]
                    ],
                    colWidths=[400, 140],
                )
                row_table.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ])
                )
                exp_elements.append(row_table)

                desc = exp.get("description") or exp.get("details")
                if desc:
                    desc_esc = xml_escape(desc).replace("\n", "<br/>")
                    exp_elements.append(Paragraph(desc_esc, body_style))

                exp_elements.append(Spacer(1, 4))
                story.append(KeepTogether(exp_elements))

            story.append(Spacer(1, 4))

        # =================================================================
        # 6. Education Section
        # =================================================================
        education_list = portfolio.get_education_list()
        if education_list:
            story.append(Paragraph("EDUCATION & ACADEMICS", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))

            for edu in education_list:
                edu_elements = []
                degree = xml_escape(edu.get("degree") or edu.get("title") or "Degree Program")
                school = xml_escape(edu.get("institution") or edu.get("school") or "")
                year = xml_escape(edu.get("year") or edu.get("duration") or "")

                edu_table = Table(
                    [
                        [
                            Paragraph(f"<b>{degree}</b>" + (f", {school}" if school else ""), item_title_style),
                            Paragraph(year, item_meta_style),
                        ]
                    ],
                    colWidths=[420, 120],
                )
                edu_table.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ])
                )
                edu_elements.append(edu_table)

                details = edu.get("details") or edu.get("gpa")
                if details:
                    edu_elements.append(Paragraph(xml_escape(details), body_style))

                edu_elements.append(Spacer(1, 4))
                story.append(KeepTogether(edu_elements))

            story.append(Spacer(1, 4))

        # =================================================================
        # 7. Licenses & Certifications
        # =================================================================
        certifications_list = portfolio.get_certifications_list()
        if certifications_list:
            story.append(Paragraph("CERTIFICATIONS & LICENSES", section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=6))

            for cert in certifications_list:
                if isinstance(cert, dict):
                    name = xml_escape(cert.get("name") or "")
                    issuer = xml_escape(cert.get("issuer") or "")
                    year = xml_escape(cert.get("year") or "")
                    label = f"<b>{name}</b>" + (f" ({issuer})" if issuer else "")
                else:
                    label = f"<b>{xml_escape(str(cert))}</b>"
                    year = ""

                cert_table = Table(
                    [
                        [
                            Paragraph(label, body_style),
                            Paragraph(year, item_meta_style),
                        ]
                    ],
                    colWidths=[420, 120],
                )
                cert_table.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ])
                )
                story.append(cert_table)

        # Build document with running header/footer
        try:
            doc.build(story, canvasmaker=NumberedCanvas)
        except Exception as e:
            raise PDFGenerationError(f"ReportLab failed to compile portfolio PDF: {str(e)}")

        buffer.seek(0)
        return buffer
