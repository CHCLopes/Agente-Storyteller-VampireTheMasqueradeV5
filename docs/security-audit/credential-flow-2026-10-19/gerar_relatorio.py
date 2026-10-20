"""Reproduce scoped, redacted audit PDF. No network or runtime credentials."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SURFACES=(
    'scripts/luna_credential_supervisor.py','scripts/run_luna_credential_supervisor.ps1',
    'scripts/evaluate_openai_luna_low_live.py','scripts/evaluate_hybrid_campaign_luna_l25_live.py',
    'scripts/evaluate_hybrid_campaign_luna_l26_live.py','scripts/run_hybrid_campaign_luna_l25_live.ps1',
    'scripts/run_hybrid_campaign_luna_l26_live.ps1','tests/test_luna_credential_supervisor.py',
    'tests/test_luna_credential_input_audit.py','tests/test_luna_test_cost.py',
)
data=json.loads((HERE/'dados-relatorio.json').read_text(encoding='utf-8'))
INDICATOR=re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{25,})\b|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----')


def indicators(text,path,revision=None):
    # Deliberately emit only locations/classification, never matched material.
    return [{'file':path,'line':n,'revision':revision,'classification':
             'synthetic_or_placeholder' if any(x in match.group().lower() for x in
              ('synthetic','test','example','placeholder')) else 'review_required'}
            for n,line in enumerate(text.splitlines(),1) for match in INDICATOR.finditer(line)]


scan={'scope':list(SURFACES),'current_indicators':[],'history_indicators':[],
      'history_blobs':0,'http_handlers':[], 'excluded':['.env*','clipboard','process memory/environment',
      'user saves','whole-product bundles','unrelated repository history']}
for relative in SURFACES:
    text=(ROOT/relative).read_text(encoding='utf-8')
    scan['current_indicators']+=indicators(text,relative)
    if relative.endswith('.py'):
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    call=decorator.func if isinstance(decorator,ast.Call) else decorator
                    if isinstance(call,ast.Attribute) and call.attr in ('get','post','put','patch','delete','websocket','route'):
                        scan['http_handlers'].append({'file':relative,'line':node.lineno})
    revisions=subprocess.check_output(['git','log','--format=%H','--',relative],cwd=ROOT,text=True).splitlines()
    for revision in revisions:
        result=subprocess.run(['git','show',f'{revision}:{relative}'],cwd=ROOT,capture_output=True)
        if result.returncode==0:
            scan['history_blobs']+=1
            scan['history_indicators']+=indicators(result.stdout.decode('utf-8',errors='replace'),relative,revision)
(HERE/'cobertura-scan.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

font=Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Audit',str(font/'arial.ttf')))
pdfmetrics.registerFont(TTFont('AuditBold',str(font/'arialbd.ttf')))
pdfmetrics.registerFontFamily('Audit',normal='Audit',bold='AuditBold',italic='Audit',boldItalic='AuditBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyAudit',fontName='Audit',fontSize=9,leading=13,spaceAfter=7))
styles.add(ParagraphStyle(name='TitleAudit',fontName='AuditBold',fontSize=24,leading=29,spaceAfter=18,textColor=colors.HexColor('#14273E')))
styles.add(ParagraphStyle(name='HeaderAudit',fontName='AuditBold',fontSize=15,leading=20,spaceAfter=12,textColor=colors.HexColor('#14273E')))
styles.add(ParagraphStyle(name='SmallAudit',fontName='Audit',fontSize=8,leading=11,spaceAfter=6,wordWrap='CJK'))
story=[]
def p(value,style='BodyAudit'):return Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
def title(value):story.append(p(value,'HeaderAudit'))
def table(rows,widths):
    t=Table([[p(c,'SmallAudit') for c in row] for row in rows],colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E2E8F0')),
                          ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#CBD5E1')),
                          ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                          ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return t
def footer(canvas,doc):
    canvas.setFont('Audit',7);canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(2*cm,1.1*cm,'Agente Storyteller | Credenciais | 19/10/2026')
    canvas.drawRightString(19*cm,1.1*cm,f'Página {doc.page}')

story.extend([Spacer(1,1*cm),p('Relatório de Auditoria de Segurança','TitleAudit'),
              p('Agente Storyteller - aplicação receptora da credencial','HeaderAudit'),p(data['date']),
              p(data['scope']),p(data['stack']),p(data['conclusion']),Spacer(1,.5*cm)])
title('Resumo e classificação')
story.append(p('0 vulnerabilidades de segurança demonstradas. 3 achados informativos de funcionamento/UX corrigidos. Informativos não entram na contagem de vulnerabilidades; o ambiente real não foi certificado.'))
chart=Drawing(470,150)
chart.add(Circle(70,72,48,fillColor=colors.HexColor('#CBD5E1'),strokeColor=None))
chart.add(Circle(70,72,29,fillColor=colors.white,strokeColor=None))
chart.add(String(70,67,'0',fontName='AuditBold',fontSize=18,textAnchor='middle'))
chart.add(String(70,8,'Vulnerabilidades',fontName='Audit',fontSize=9,textAnchor='middle'))
bars=VerticalBarChart();bars.x=160;bars.y=35;bars.width=285;bars.height=90
bars.data=[(0,0,0,0,0)];bars.categoryAxis.categoryNames=['Dono','Permissão','IDOR','Segredos','XSS']
bars.valueAxis.valueMin=0;bars.valueAxis.valueMax=1;bars.valueAxis.valueStep=1
bars.bars[0].fillColor=colors.HexColor('#64748B');chart.add(bars)
story.extend([chart,p('Paleta de severidade: crítica #B91C1C; alta #EA580C; média #D97706; baixa #2563EB; informativa #64748B. Não há fatias artificiais para categorias com zero achados de segurança.','SmallAudit'),PageBreak()])
title('Cobertura e limites por categoria')
story.append(table([['Categoria','Resultado e evidência']]+[[c['category'],c['result']+' - '+c['reason']] for c in data['coverage']],[4*cm,13*cm]))
story.append(Spacer(1,.4*cm));title('Proteções verificadas')
for value in data['strengths']:story.append(p('• '+value))
story.extend([p(f"Scan delimitado: {len(SURFACES)} arquivos, {scan['history_blobs']} blobs históricos, {len(scan['http_handlers'])} handlers HTTP. Indicadores são metadados mascarados; classificação não é validação de credencial.",'SmallAudit'),PageBreak()])
title('Achados por arquivo e linha atual')
story.append(table([['ID / severidade','Arquivo:linha atual','Descrição']]+[
    [f['id']+' / '+f['severity'],f["file"]+':'+str(f['line']),f['title']] for f in data['findings']],[2.6*cm,7.2*cm,7.2*cm]))
story.append(p('Linhas atuais apontam a correção. A descrição anterior foi observada antes da edição nesta tarefa, sem commit intermediário; não representa trecho vulnerável ainda presente.','SmallAudit'))
for finding in data['findings']:
    block=[p(finding['id']+' - '+finding['title'],'HeaderAudit')]
    for label,key in [('Antes','before'),('Condição','condition'),('Impacto','impact'),('Correção','correction'),('Evidência','evidence'),('Estado','status')]:
        block.append(p(label+': '+finding[key]))
    story.append(KeepTogether(block))
story.append(PageBreak());title('Verificação, recomendações e limitações')
for value in data['verification']+data['recommendations']+data['limitations']:story.append(p('• '+value))
issues=[]
for number,f in enumerate(data['findings'],1):
    issue=(f"--- ISSUE {number} ---\n# [Segurança] {f['title']}\n"
           f"Labels sugeridas: security, informativa\n\nEstado: corrigido nas fontes; rascunho não publicado.\n\n"
           f"Problema: {f['before']}\nCondição: {f['condition']}\nImpacto: {f['impact']}\n"
           f"Evidência atual: {f['file']}:{f['line']}. {f['evidence']}\n"
           f"Correção: {f['correction']}\nCritérios de aceite:\n"+
           '\n'.join('- [x] '+item for item in f['acceptance'])+f'\n--- FIM ISSUE {number} ---\n')
    issues.append(issue)
story.append(PageBreak());title('ISSUES PARA O GITHUB')
story.append(p('Rascunhos de rastreabilidade de achados informativos já corrigidos; não foram publicados e não alegam vulnerabilidade remota.'))
for issue in issues:story.append(KeepTogether([p(issue,'SmallAudit'),Spacer(1,.3*cm)]))
(HERE/'issues.md').write_text('\n'.join(issues),encoding='utf-8')
pdf=HERE/'relatorio-auditoria-seguranca.pdf'
SimpleDocTemplate(str(pdf),pagesize=(21*cm,29.7*cm),leftMargin=2*cm,rightMargin=2*cm,
                  topMargin=1.8*cm,bottomMargin=2*cm,title='Auditoria do fluxo de credencial - Agente Storyteller').build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(str(pdf));text='\n'.join(page.extract_text() or '' for page in reader.pages)
assert all(f['id'] in text for f in data['findings']) and 'ISSUES PARA O GITHUB' in text
manifest={'date':data['date'],'pages':len(reader.pages),'informational_findings':len(data['findings']),
          'security_vulnerabilities_demonstrated':0,'http_handlers':len(scan['http_handlers']),
          'surfaces_sha256':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SURFACES},
          'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}
(HERE/'manifesto-auditoria.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
previews=HERE/'previews';previews.mkdir(exist_ok=True)
document=pdfium.PdfDocument(str(pdf));tiles=[]
for number in range(len(document)):
    page=document[number].render(scale=1.1).to_pil().convert('RGB')
    page.save(previews/f'pagina-{number+1:02}.png');page.thumbnail((330,470))
    tile=Image.new('RGB',(350,500),'white');tile.paste(page,((350-page.width)//2,10))
    ImageDraw.Draw(tile).text((12,480),f'Pagina {number+1}',fill='black');tiles.append(tile)
sheet=Image.new('RGB',(700,500*((len(tiles)+1)//2)),'#dce3eb')
for index,tile in enumerate(tiles):sheet.paste(tile,((index%2)*350,(index//2)*500))
sheet.save(previews/'visao-geral.png')
print(json.dumps({'pages':len(reader.pages),'informational_findings':len(data['findings']),
                  'history_blobs':scan['history_blobs'],'current_indicators':len(scan['current_indicators']),
                  'history_indicators':len(scan['history_indicators']),'pdf':str(pdf)},ensure_ascii=False))
