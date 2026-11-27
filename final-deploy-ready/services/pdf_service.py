import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_student_report_pdf(student, skills_list, top_career, roadmap_items):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    navy = colors.HexColor('#0F2942')
    slate = colors.HexColor('#334155')
    light_bg = colors.HexColor('#F1F5F9')

    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=18, textColor=navy, spaceAfter=6)
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=13, textColor=navy, spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=10, textColor=slate, leading=14)

    elements = []

    # Header
    elements.append(Paragraph("SKILL GAP ANALYSIS & CAREER RECOMMENDATION REPORT", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    elements.append(Spacer(1, 12))

    # 1. Student Profile
    elements.append(Paragraph("1. Student Profile Summary", h2_style))
    profile_data = [
        ["Student ID:", student['student_code'], "Full Name:", student['full_name']],
        ["Email:", student['email'], "Department:", student['department'] or 'N/A'],
        ["Semester:", str(student['semester']), "Career Interests:", student['career_interests'] or 'Not Specified']
    ]
    profile_table = Table(profile_data, colWidths=[90, 160, 100, 165])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), light_bg),
        ('BACKGROUND', (2, 0), (2, -1), light_bg),
        ('TEXTCOLOR', (0, 0), (-1, -1), slate),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(profile_table)

    # 2. Current Skill Assessment
    elements.append(Paragraph("2. Recorded Skill Proficiency (Scale: 0 - 5)", h2_style))
    skill_table_data = [["Skill Name", "Category", "Current Proficiency"]]
    for s in skills_list:
        skill_table_data.append([s['name'], s['category'], f"{s['proficiency']} / 5"])

    skill_table = Table(skill_table_data, colWidths=[200, 180, 135])
    skill_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(skill_table)

    # 3. Primary Career Recommendation & Skill Gap
    elements.append(Paragraph("3. Top Career Match & Skill Gap Breakdown", h2_style))
    if top_career:
        elements.append(Paragraph(
            f"<b>Recommended Career:</b> {top_career['career_title']} "
            f"(Compatibility Score: {top_career['match_percentage']}%)",
            body_style
        ))
        elements.append(Spacer(1, 6))
        gap_data = [["Required Skill", "Current", "Required", "Skill Gap", "Status"]]
        for b in top_career['breakdown']:
            gap_data.append([
                b['skill_name'],
                str(b['current_proficiency']),
                str(b['required_proficiency']),
                str(b['gap']),
                b['status']
            ])
        gap_table = Table(gap_data, colWidths=[165, 75, 75, 75, 125])
        gap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        elements.append(gap_table)
    else:
        elements.append(Paragraph("No assessment data available to compute career match.", body_style))

    # 4. Learning Roadmap
    elements.append(Paragraph("4. Personalized Learning Roadmap", h2_style))
    if roadmap_items:
        road_data = [["Skill", "Target", "Priority", "Status", "Recommended Focus Topics"]]
        for item in roadmap_items:
            road_data.append([
                item['skill_name'],
                f"Level {item['target_proficiency']}",
                item['priority'],
                item['status'],
                Paragraph(item['suggested_topics'], body_style)
            ])
        road_table = Table(road_data, colWidths=[95, 55, 60, 80, 225])
        road_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        elements.append(road_table)
    else:
        elements.append(Paragraph("No active skill gaps identified for the selected career track.", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer