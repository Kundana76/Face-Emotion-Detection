"""
PDF Report Generator
Produces professional session reports using ReportLab.
"""

import os
from datetime import datetime

from reportlab.lib.pagesizes  import letter
from reportlab.lib            import colors
from reportlab.lib.units      import inch
from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums      import TA_CENTER, TA_LEFT
from reportlab.platypus       import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether
)


REPORTS_DIR = 'reports'

# Colour palette
C_DARK      = colors.HexColor('#0d1117')
C_BLUE      = colors.HexColor('#58a6ff')
C_GREEN     = colors.HexColor('#3fb950')
C_YELLOW    = colors.HexColor('#d29922')
C_RED       = colors.HexColor('#f85149')
C_PURPLE    = colors.HexColor('#8b949e')
C_BG        = colors.HexColor('#161b22')
C_WHITE     = colors.white

EMOTION_INSIGHT = {
    'happy':    ("Positive", C_GREEN,
                 "Predominantly happy emotional states were detected. Participants appear "
                 "engaged and comfortable. The environment successfully promotes positive "
                 "emotional well-being. Recommend maintaining current conditions."),
    'neutral':  ("Calm", C_BLUE,
                 "Mostly neutral states indicate composed, focused participants. "
                 "Consider introducing activities to boost positive engagement and "
                 "reduce monotony if sessions are prolonged."),
    'sad':      ("Concern", C_YELLOW,
                 "Elevated sadness levels may indicate discomfort or low morale. "
                 "Recommend reviewing session content, scheduling breaks, and "
                 "checking in individually with participants."),
    'angry':    ("Alert", C_RED,
                 "High anger levels were detected — immediate attention recommended. "
                 "Review session recordings for triggers, consider conflict-resolution "
                 "strategies, and follow up with affected individuals."),
    'fear':     ("Alert", C_RED,
                 "Fear responses suggest participants may be experiencing anxiety or stress. "
                 "Create a safer, more supportive environment and consider reducing "
                 "pressure-inducing elements."),
    'surprise': ("Varied", C_YELLOW,
                 "High surprise indicates unexpected events during the session. "
                 "Evaluate whether surprises were positive (engagement) or negative "
                 "(discomfort) from contextual data."),
    'disgust':  ("Concern", C_RED,
                 "Disgust responses were detected. Review session content for elements "
                 "causing negative reactions and adjust accordingly."),
}


class ReportGenerator:
    def __init__(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def generate(self, stats: dict, logs: list, timeline: list) -> str:
        path = os.path.join(
            REPORTS_DIR,
            f'FEIS_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

        doc    = SimpleDocTemplate(
            path, pagesize=letter,
            leftMargin=0.75*inch, rightMargin=0.75*inch,
            topMargin=0.75*inch,  bottomMargin=0.75*inch
        )
        styles = getSampleStyleSheet()
        story  = []

        # ── Header ──────────────────────────────────────────────────
        title_style = ParagraphStyle(
            'FEISTitle', parent=styles['Title'],
            fontSize=22, textColor=C_BLUE,
            spaceAfter=4, alignment=TA_CENTER
        )
        sub_style = ParagraphStyle(
            'FEISSub', parent=styles['Normal'],
            fontSize=10, textColor=C_PURPLE,
            alignment=TA_CENTER, spaceAfter=16
        )

        story.append(Paragraph("🧠  FEIS — Face Emotion Intelligence System", title_style))
        story.append(Paragraph(
            f"Session Report  ·  Generated {datetime.now().strftime('%B %d, %Y  %H:%M:%S')}",
            sub_style
        ))
        story.append(HRFlowable(width='100%', thickness=1, color=C_BLUE))
        story.append(Spacer(1, 0.2*inch))

        # ── Summary Cards ────────────────────────────────────────────
        total    = stats.get('total_detections', 0)
        dominant = stats.get('dominant_emotion', 'none').title()
        latest   = stats.get('latest_emotion',  'none').title()

        summary_data = [
            ['Total Detections', 'Dominant Emotion', 'Latest Emotion'],
            [str(total),          dominant,            latest],
        ]
        t = Table(summary_data, colWidths=[2.2*inch]*3, hAlign='CENTER')
        t.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0), C_DARK),
            ('TEXTCOLOR',    (0, 0), (-1, 0), C_BLUE),
            ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',     (0, 0), (-1, 0), 10),
            ('BACKGROUND',   (0, 1), (-1, 1), C_BG),
            ('TEXTCOLOR',    (0, 1), (-1, 1), C_WHITE),
            ('FONTNAME',     (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0, 1), (-1, 1), 16),
            ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [C_DARK, C_BG]),
            ('BOX',          (0, 0), (-1, -1), 1.5, C_BLUE),
            ('INNERGRID',    (0, 0), (-1, -1), 0.5, C_PURPLE),
            ('TOPPADDING',   (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.25*inch))

        # ── Emotion Distribution ──────────────────────────────────────
        h1 = ParagraphStyle('H1', parent=styles['Heading1'],
                             fontSize=13, textColor=C_BLUE, spaceBefore=10, spaceAfter=6)
        story.append(Paragraph("Emotion Distribution", h1))

        counts   = stats.get('emotion_counts', {})
        avg_conf = stats.get('avg_confidence', {})

        if counts:
            emo_data = [['Emotion', 'Detections', 'Share %', 'Avg Confidence']]
            total_cnt = sum(counts.values()) or 1
            for emo, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                share = round(cnt / total_cnt * 100, 1)
                ac    = avg_conf.get(emo, 0)
                emo_data.append([emo.title(), str(cnt), f"{share}%", f"{ac:.1f}%"])

            t2 = Table(emo_data, colWidths=[1.8*inch, 1.4*inch, 1.3*inch, 1.8*inch], hAlign='LEFT')
            t2.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, 0), C_DARK),
                ('TEXTCOLOR',    (0, 0), (-1, 0), C_GREEN),
                ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 9),
                ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1c2128'), C_BG]),
                ('TEXTCOLOR',    (0, 1), (-1, -1), colors.HexColor('#c9d1d9')),
                ('GRID',         (0, 0), (-1, -1), 0.4, C_PURPLE),
                ('TOPPADDING',   (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
            ]))
            story.append(t2)
        else:
            story.append(Paragraph("No emotion data recorded yet.", styles['Normal']))

        story.append(Spacer(1, 0.2*inch))

        # ── AI Insights ──────────────────────────────────────────────
        story.append(Paragraph("AI Psychological Insights", h1))

        dom_key    = stats.get('dominant_emotion', 'neutral').lower()
        ins        = EMOTION_INSIGHT.get(dom_key, EMOTION_INSIGHT['neutral'])
        ins_label, ins_color, ins_text = ins

        ins_style = ParagraphStyle(
            'Insight', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#c9d1d9'),
            backColor=C_BG, borderPad=10,
            leading=16, leftIndent=10, rightIndent=10
        )
        badge_style = ParagraphStyle(
            'Badge', parent=styles['Normal'],
            fontSize=11, textColor=ins_color,
            fontName='Helvetica-Bold', spaceAfter=4
        )
        story.append(Paragraph(f"Status: {ins_label}", badge_style))
        story.append(Paragraph(
            f"Based on {total} total detections, the dominant emotional state was "
            f"<b>{dom_key.title()}</b>. {ins_text}", ins_style
        ))
        story.append(Spacer(1, 0.2*inch))

        # ── Recent Log ───────────────────────────────────────────────
        story.append(Paragraph("Recent Detection Log (last 30)", h1))

        if logs:
            log_data = [['#', 'Time', 'Face', 'Emotion', 'Confidence']]
            for i, lg in enumerate(logs[:30], 1):
                ts = lg.get('timestamp', '')[:19].replace('T', ' ')
                log_data.append([
                    str(i),
                    ts,
                    f"#{lg.get('face_id', '?')}",
                    lg.get('emotion', '').title(),
                    f"{lg.get('confidence', 0):.1f}%"
                ])
            t3 = Table(log_data,
                       colWidths=[0.4*inch, 2.2*inch, 0.6*inch, 1.4*inch, 1.2*inch],
                       hAlign='LEFT')
            t3.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, 0), C_DARK),
                ('TEXTCOLOR',    (0, 0), (-1, 0), C_PURPLE),
                ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 8),
                ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1c2128'), C_BG]),
                ('TEXTCOLOR',    (0, 1), (-1, -1), colors.HexColor('#c9d1d9')),
                ('GRID',         (0, 0), (-1, -1), 0.3, C_PURPLE),
                ('TOPPADDING',   (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
            ]))
            story.append(t3)
        else:
            story.append(Paragraph("No detections logged.", styles['Normal']))

        # ── Footer ───────────────────────────────────────────────────
        story.append(Spacer(1, 0.3*inch))
        story.append(HRFlowable(width='100%', thickness=0.5, color=C_PURPLE))
        foot_style = ParagraphStyle(
            'Footer', parent=styles['Normal'],
            fontSize=8, textColor=C_PURPLE, alignment=TA_CENTER, spaceBefore=6
        )
        story.append(Paragraph(
            "FEIS — Face Emotion Intelligence System  ·  Confidential Report  ·  "
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            foot_style
        ))

        doc.build(story)
        print(f"📄  Report saved: {path}")
        return path
