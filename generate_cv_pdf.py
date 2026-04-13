#!/usr/bin/env python3
"""
Generate professional CV PDFs for Alejandro Hernandez Loza.
Creates both English (cv_alejandro_en.pdf) and Spanish (cv_alejandro_es.pdf).
"""
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# Colors
DARK_BLUE = HexColor('#1a237e')
MEDIUM_BLUE = HexColor('#1565c0')
LIGHT_BLUE = HexColor('#e3f2fd')
ACCENT = HexColor('#0d47a1')
GRAY = HexColor('#546e7a')
LIGHT_GRAY = HexColor('#f5f5f5')
TEXT = HexColor('#212121')
WHITE = white


def build_cv(lang='en'):
    with open('data/resume.json') as f:
        r = json.load(f)

    p = r['personal']
    is_es = lang == 'es'
    filename = f"data/cv_alejandro_{lang}.pdf"

    # Labels
    L = {
        'summary': 'Professional Summary' if not is_es else 'Resumen Profesional',
        'experience': 'Professional Experience' if not is_es else 'Experiencia Profesional',
        'skills': 'Technical Skills' if not is_es else 'Habilidades Técnicas',
        'education': 'Education' if not is_es else 'Educación',
        'languages': 'Languages' if not is_es else 'Idiomas',
        'present': 'Present' if not is_es else 'Actual',
        'languages_label': 'Languages' if not is_es else 'Idiomas',
        'frameworks_label': 'Frameworks' if not is_es else 'Frameworks',
        'cloud_label': 'Cloud' if not is_es else 'Cloud',
        'devops_label': 'DevOps' if not is_es else 'DevOps',
        'databases_label': 'Databases' if not is_es else 'Bases de Datos',
        'architecture_label': 'Architecture' if not is_es else 'Arquitectura',
        'available': 'Immediately available' if not is_es else 'Disponibilidad inmediata',
        'remote': 'Remote / Mexico City' if not is_es else 'Remoto / Ciudad de México',
    }

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=1.8*cm,
        rightMargin=1.8*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    name_style = ParagraphStyle('Name', fontSize=26, textColor=WHITE, fontName='Helvetica-Bold', leading=30)
    title_style = ParagraphStyle('Title', fontSize=13, textColor=LIGHT_BLUE, fontName='Helvetica', leading=18)
    contact_style = ParagraphStyle('Contact', fontSize=9, textColor=WHITE, fontName='Helvetica', leading=14)
    section_header = ParagraphStyle('SectionHeader', fontSize=12, textColor=DARK_BLUE, fontName='Helvetica-Bold',
                                    spaceBefore=8, spaceAfter=4)
    job_title_style = ParagraphStyle('JobTitle', fontSize=11, textColor=TEXT, fontName='Helvetica-Bold', leading=14)
    company_style = ParagraphStyle('Company', fontSize=10, textColor=MEDIUM_BLUE, fontName='Helvetica-Bold', leading=13)
    date_style = ParagraphStyle('Date', fontSize=9, textColor=GRAY, fontName='Helvetica', leading=12)
    body_style = ParagraphStyle('Body', fontSize=9.5, textColor=TEXT, fontName='Helvetica', leading=13, spaceAfter=3)
    bullet_style = ParagraphStyle('Bullet', fontSize=9, textColor=TEXT, fontName='Helvetica', leading=12,
                                  leftIndent=10, bulletIndent=0, spaceAfter=2)
    skill_label_style = ParagraphStyle('SkillLabel', fontSize=9, textColor=DARK_BLUE, fontName='Helvetica-Bold', leading=12)
    skill_value_style = ParagraphStyle('SkillValue', fontSize=9, textColor=TEXT, fontName='Helvetica', leading=12)

    story = []

    # === HEADER (dark blue background) ===
    header_name = Paragraph(p['name'], name_style)
    header_title = Paragraph(p['title'], title_style)
    contact_line = (
        f"{p['email']}  •  {p['phone']}  •  {p['location']}  •  linkedin.com/in/alejandro-hernandez-loza"
    )
    header_contact = Paragraph(contact_line, contact_style)

    avail_line = f"✓ {L['available']}  |  {L['remote']}"
    header_avail = Paragraph(avail_line, ParagraphStyle('Avail', fontSize=9, textColor=HexColor('#b3e5fc'),
                                                        fontName='Helvetica-Oblique'))

    header_table = Table(
        [[header_name], [header_title], [Spacer(1, 4)], [header_contact], [header_avail]],
        colWidths=[doc.width],
    )
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # === SUMMARY ===
    story.append(Paragraph(L['summary'], section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_BLUE, spaceAfter=5))

    summary_text = r['summary'] if is_es else (
        "Senior Software Engineer with 12+ years of experience in Full Stack development, "
        "specialized in Java, Spring Boot, and microservices architecture. Experience leading "
        "development teams and building scalable cloud systems (AWS/GCP). Proven track record at "
        "companies like Thomson Reuters and Kubo Financiero. Open to remote or hybrid positions."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    # === EXPERIENCE ===
    story.append(Paragraph(L['experience'], section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_BLUE, spaceAfter=5))

    exp_en = [
        {
            "company": "Thomson Reuters",
            "title": "Senior Software Engineer",
            "location": "Mexico City (Remote)",
            "start_date": "2022", "end_date": "2024",
            "description": "Led development of AI agent using Claude Code to automate internal productivity tools. Worked with Java, Spring Boot and microservices architectures in cloud environments.",
            "achievements": [
                "Developed AI agent with Claude Code for productivity tool automation",
                "Implemented Java/Spring Boot microservices solutions",
                "Contributed to high-volume legal data platforms",
            ],
            "technologies": ["Java", "Spring Boot", "Microservices", "AWS", "Claude Code", "Python"]
        },
        {
            "company": "Kubo Financiero",
            "title": "Senior Software Engineer",
            "location": "Mexico City",
            "start_date": "2019", "end_date": "2022",
            "description": "Migrated monolithic architecture to microservices, improving scalability and reducing latency. Full stack development with Java and JavaScript.",
            "achievements": [
                "Microservices migration: +20% scalability, -15% latency",
                "Implementation of high-performance REST APIs",
                "Technical leadership of development team",
            ],
            "technologies": ["Java", "Spring Boot", "Microservices", "JavaScript", "Angular", "Docker", "GCP"]
        },
        {
            "company": "Previous Experience",
            "title": "Software Engineer / Senior Developer",
            "location": "Mexico City",
            "start_date": "2012", "end_date": "2019",
            "description": "7+ years of progressive experience in enterprise Java development across multiple industries.",
            "achievements": [
                "Led backend development for financial and enterprise applications",
                "Designed RESTful APIs and database schemas for high-traffic systems",
                "Mentored junior developers and defined coding standards",
            ],
            "technologies": ["Java", "Spring", "Hibernate", "Oracle", "MySQL", "AngularJS"]
        },
    ]

    experiences = r['experience'] if is_es else exp_en

    for exp in experiences:
        end = exp.get('end_date', L['present'])
        if end in ('2024', 'Actual', 'Present') and exp['company'] == 'Thomson Reuters':
            end = L['present']

        # Company + Date row
        row = Table(
            [[Paragraph(f"<b>{exp['title']}</b>", job_title_style),
              Paragraph(f"{exp['start_date']} – {end}", date_style)]],
            colWidths=[doc.width * 0.72, doc.width * 0.28],
        )
        row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(row)
        story.append(Paragraph(f"{exp['company']}  |  {exp.get('location', '')}", company_style))
        story.append(Paragraph(exp['description'], body_style))

        for ach in exp.get('achievements', []):
            story.append(Paragraph(f"• {ach}", bullet_style))

        tech_line = "  ".join(exp.get('technologies', []))
        story.append(Paragraph(
            f"<font color='#1565c0'><b>Tech:</b></font> {tech_line}",
            ParagraphStyle('Tech', fontSize=8.5, textColor=GRAY, fontName='Helvetica', leading=12, spaceAfter=8)
        ))

    # === SKILLS ===
    story.append(Spacer(1, 4))
    story.append(Paragraph(L['skills'], section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_BLUE, spaceAfter=5))

    sk = r['skills']
    skill_rows = [
        (L['languages_label'], ", ".join(sk['languages'])),
        (L['frameworks_label'], ", ".join(sk['frameworks'])),
        (L['cloud_label'], ", ".join(sk['cloud'])),
        (L['devops_label'], ", ".join(sk['devops'])),
        (L['databases_label'], ", ".join(sk['databases'])),
        (L['architecture_label'], ", ".join(sk['architecture'])),
    ]

    skill_table_data = []
    for label, value in skill_rows:
        skill_table_data.append([
            Paragraph(label, skill_label_style),
            Paragraph(value, skill_value_style),
        ])

    skill_table = Table(skill_table_data, colWidths=[doc.width * 0.22, doc.width * 0.78])
    skill_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT_GRAY, WHITE]),
    ]))
    story.append(skill_table)

    # === EDUCATION + LANGUAGES (two columns) ===
    story.append(Spacer(1, 8))

    edu_content = []
    edu_content.append(Paragraph(L['education'], section_header))
    edu_content.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_BLUE, spaceAfter=5))
    for edu in r['education']:
        edu_content.append(Paragraph(f"<b>{edu['institution']}</b>", job_title_style))
        edu_content.append(Paragraph(edu['degree'], body_style))
        edu_content.append(Paragraph(str(edu['year']), date_style))

    lang_content = []
    lang_content.append(Paragraph(L['languages'], section_header))
    lang_content.append(HRFlowable(width="100%", thickness=1, color=MEDIUM_BLUE, spaceAfter=5))
    for lng in r['languages']:
        lang_content.append(Paragraph(f"<b>{lng['language']}</b>: {lng['level']}", body_style))

    bottom_table = Table(
        [[edu_content, lang_content]],
        colWidths=[doc.width * 0.65, doc.width * 0.35],
    )
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(bottom_table)

    doc.build(story)
    print(f"Generated: {filename}")
    return filename


if __name__ == '__main__':
    build_cv('en')
    build_cv('es')
    print("Both CVs generated successfully.")
