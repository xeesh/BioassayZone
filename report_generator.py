from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import Image as ReportLabImage
from datetime import datetime
from typing import Dict, List, Any
import os

class ReportGenerator:
    """Generates PDF reports for bioassay zone measurements"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='DataLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            leftIndent=20
        ))
    
    def create_report(self, report_data: Dict[str, Any], output_path: str):
        """
        Create a comprehensive PDF report
        
        Args:
            report_data: Dictionary containing assay data, zones, statistics, and audit trail
            output_path: Path where the PDF report will be saved
        """
        try:
            # Create document
            doc = SimpleDocTemplate(output_path, pagesize=A4, 
                                  topMargin=0.5*inch, bottomMargin=0.5*inch,
                                  leftMargin=0.5*inch, rightMargin=0.5*inch)
            
            # Build story (content)
            story = []
            
            # Title page
            story.extend(self._create_title_section(report_data))
            
            # Assay information
            story.extend(self._create_assay_info_section(report_data))
            
            # Zone measurements
            story.extend(self._create_measurements_section(report_data))
            
            # Statistics
            story.extend(self._create_statistics_section(report_data))
            
            # Audit trail
            story.extend(self._create_audit_section(report_data))
            
            # Build PDF
            doc.build(story)
            
        except Exception as e:
            raise Exception(f"Report generation failed: {str(e)}")
    
    def _create_title_section(self, report_data: Dict[str, Any]) -> List:
        """Create the title section of the report"""
        story = []
        
        # Main title
        title = Paragraph("Bioassay Zone Measurement Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Report generation info
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info_text = f"<b>Generated:</b> {generation_time}<br/>"
        info_text += f"<b>Report ID:</b> {report_data['assay']['id']}"
        
        info_para = Paragraph(info_text, self.styles['Normal'])
        story.append(info_para)
        story.append(Spacer(1, 30))
        
        return story
    
    def _create_assay_info_section(self, report_data: Dict[str, Any]) -> List:
        """Create the assay information section"""
        story = []
        assay = report_data['assay']
        
        # Section header
        header = Paragraph("Assay Information", self.styles['SectionHeader'])
        story.append(header)
        
        # Assay details table
        assay_data = [
            ['Assay Name:', assay.get('assay_name', 'N/A')],
            ['Analyst:', assay.get('analyst_name', 'N/A')],
            ['Sample Type:', assay.get('sample_type', 'N/A')],
            ['Analysis Date:', assay.get('timestamp', 'N/A')[:10]],
            ['Image File:', assay.get('filename', 'N/A')]
        ]
        
        assay_table = Table(assay_data, colWidths=[2*inch, 4*inch])
        assay_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(assay_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_measurements_section(self, report_data: Dict[str, Any]) -> List:
        """Create the zone measurements section"""
        story = []
        zones = report_data.get('zones', [])
        
        # Section header
        header = Paragraph("Zone Measurements", self.styles['SectionHeader'])
        story.append(header)
        
        if not zones:
            no_data = Paragraph("No zone measurements recorded.", self.styles['Normal'])
            story.append(no_data)
            story.append(Spacer(1, 20))
            return story
        
        # Measurements table
        table_data = [['Zone ID', 'Type', 'X Position', 'Y Position', 'Diameter (mm)', 'Confidence']]
        
        for zone in zones:
            confidence = zone.get('confidence', 'N/A')
            if isinstance(confidence, float):
                confidence = f"{confidence:.2f}"
            
            table_data.append([
                zone.get('id', 'N/A'),
                zone.get('type', 'N/A'),
                str(zone.get('x', 'N/A')),
                str(zone.get('y', 'N/A')),
                str(zone.get('diameter_mm', 'N/A')),
                str(confidence)
            ])
        
        measurements_table = Table(table_data, colWidths=[1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        measurements_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(measurements_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_statistics_section(self, report_data: Dict[str, Any]) -> List:
        """Create the statistics section"""
        story = []
        statistics = report_data.get('statistics', {})
        
        # Section header
        header = Paragraph("Statistical Analysis", self.styles['SectionHeader'])
        story.append(header)
        
        if not statistics:
            no_stats = Paragraph("No statistical analysis performed.", self.styles['Normal'])
            story.append(no_stats)
            story.append(Spacer(1, 20))
            return story
        
        # Statistics table
        stats_data = [['Statistic', 'Value', 'Unit']]
        
        stat_labels = {
            'count': 'Number of Zones',
            'mean': 'Mean Diameter',
            'median': 'Median Diameter',
            'std_dev': 'Standard Deviation',
            'min': 'Minimum Diameter',
            'max': 'Maximum Diameter',
            'range': 'Range',
            'cv_percent': 'Coefficient of Variation'
        }
        
        for key, label in stat_labels.items():
            if key in statistics:
                value = statistics[key]
                unit = 'mm' if key != 'count' and key != 'cv_percent' else ('count' if key == 'count' else '%')
                stats_data.append([label, str(value), unit])
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_audit_section(self, report_data: Dict[str, Any]) -> List:
        """Create the audit trail section"""
        story = []
        audit_trail = report_data.get('audit_trail', [])
        
        # Section header
        header = Paragraph("Audit Trail", self.styles['SectionHeader'])
        story.append(header)
        
        if not audit_trail:
            no_audit = Paragraph("No audit entries recorded.", self.styles['Normal'])
            story.append(no_audit)
            return story
        
        # Audit table
        audit_data = [['Timestamp', 'User', 'Action', 'Description']]
        
        for entry in audit_trail:
            # Convert timestamp to string and format it
            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else 'N/A'
            
            # Get user information if available
            user_info = 'N/A'
            if hasattr(entry, 'user_id') and entry.user_id:
                # Try to get username from user relationship if it exists
                if hasattr(entry, 'user') and entry.user:
                    user_info = entry.user.username
                else:
                    user_info = f"User ID: {entry.user_id}"
            
            audit_data.append([
                timestamp_str,
                user_info,
                getattr(entry, 'action', 'N/A'),
                getattr(entry, 'description', 'N/A')
            ])
        
        audit_table = Table(audit_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 2.6*inch])
        audit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        story.append(audit_table)
        
        return story
