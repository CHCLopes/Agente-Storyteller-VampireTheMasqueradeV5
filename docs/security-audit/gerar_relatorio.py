"""Generate the Portuguese security report using only local structured sources.

Run scan_local.py first. Requires reportlab, pypdf and pypdfium2 in the
bundled document runtime. No network, credentials or application execution.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, XPreformatted,
)
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PALETTE = {'crítica': '#B91C1C', 'alta': '#EA580C', 'média': '#D97706',
           'baixa': '#2563EB', 'informativa': '#64748B', 'forte': '#059669'}
FONT_DIR = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Audit', str(FONT_DIR / 'arial.ttf')))
pdfmetrics.registerFont(TTFont('AuditBold', str(FONT_DIR / 'arialbd.ttf')))
pdfmetrics.registerFontFamily('Audit', normal='Audit', bold='AuditBold',
                             italic='Audit', boldItalic='AuditBold')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyAudit', fontName='Audit', fontSize=9.4,
                          leading=14, spaceAfter=8, textColor=colors.HexColor('#263445')))
styles.add(ParagraphStyle(name='TitleAudit', fontName='AuditBold', fontSize=25,
                          leading=31, spaceAfter=18, textColor=colors.HexColor('#14273E')))
styles.add(ParagraphStyle(name='H1Audit', fontName='AuditBold', fontSize=17,
                          leading=22, spaceAfter=12, textColor=colors.HexColor('#14273E')))
styles.add(ParagraphStyle(name='H2Audit', fontName='AuditBold', fontSize=11,
                          leading=15, spaceAfter=7, textColor=colors.HexColor('#14273E')))
styles.add(ParagraphStyle(name='SmallAudit', fontName='Audit', fontSize=7.6,
                          leading=10, spaceAfter=5, wordWrap='CJK'))
styles.add(ParagraphStyle(name='CodeAudit', fontName='Courier', fontSize=7.6,
                          leading=11, spaceAfter=10, backColor=colors.HexColor('#F1F5F9'),
                          borderPadding=8))
styles.add(ParagraphStyle(name='WhiteAudit', fontName='AuditBold', fontSize=8,
                          leading=11, textColor=colors.white))
data = json.loads((HERE / 'dados-relatorio.json').read_text(encoding='utf-8'))
coverage = json.loads((HERE / 'cobertura-e-scan.json').read_text(encoding='utf-8'))
findings = data['findings']
assert len({f['id'] for f in findings}) == len(findings)
assert all(f['status'] == 'corrigido' for f in findings)
story = []


def p(value, style='BodyAudit'):
    return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])


def title(value):
    story.append(p(value, 'H1Audit'))


def item(label, value):
    story.append(p(label, 'H2Audit'))
    story.append(p(value))


def table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    settings = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, -1), .35, colors.HexColor('#D9E2EC'))]
    if header:
        settings.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14273E')))
    t.setStyle(TableStyle(settings))
    return t


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#D9E2EC'))
    canvas.line(2*cm, 1.5*cm, 19*cm, 1.5*cm)
    canvas.setFont('Audit', 7)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(2*cm, 1.1*cm, 'Agente Storyteller | Auditoria local | 16/10/2026')
    canvas.drawRightString(19*cm, 1.1*cm, f'Página {doc.page}')


story += [Spacer(1, 1.3*cm), p('RELATÓRIO TÉCNICO', 'H2Audit'),
          p('Relatório de Auditoria de Segurança', 'TitleAudit'),
          p('Agente Storyteller', 'H1Audit'), p(data['date']),
          Spacer(1, .7*cm), p(data['scope']),
          p('Estado ao encerrar: 2 achados confirmados e corrigidos; 0 pendentes entre as causas confirmadas nesta auditoria. Nenhum narrador ou release foi admitido.'),
          Spacer(1, .5*cm)]
item('Método e contrato de confiança',
     'Inventário integral dos handlers, rastreamento de serviços e persistência, reprodução sintética antes da correção e contraprovas depois. O produto aprovado tem um operador local confiável: isolamento foi mapeado para sessão, visibilidade e fronteira do navegador, não para um tenant inexistente.')
item('Snapshot e proveniência',
     f"Branch {coverage['branch']}; HEAD {coverage['head'][:12]}. O worktree contém alterações locais preexistentes; o código auditado não é o HEAD puro. Evidências anteriores não foram reescritas.")
story.append(p('Sem serviços reais, credenciais, inferência paga, instalação de dependências, publicação de issues, commit ou push.'))
story.append(PageBreak())

title('1. Resumo executivo')
story.append(p('Contagens por causa única e severidade no momento da descoberta. Os gráficos não representam vulnerabilidades ainda abertas. Isolamento e IDOR relacionados a SEC-001 não foram contados duas vezes.'))
counts = Counter(f['severity'] for f in findings)
summary = [[p('Severidade', 'WhiteAudit'), p('Confirmados', 'WhiteAudit'), p('Abertos', 'WhiteAudit')]]
for level in ('crítica', 'alta', 'média', 'baixa', 'informativa'):
    summary.append([Paragraph(f'<font color="{PALETTE[level]}">{level.upper()}</font>', styles['BodyAudit']),
                    p(counts[level]), p(0)])
story.append(table(summary, [8*cm, 4*cm, 4*cm]))
story.append(Spacer(1, .4*cm))
donut = Drawing(245, 175)
pie = Pie()
pie.x, pie.y, pie.width, pie.height = 30, 10, 135, 135
pie.data = [counts['alta'], counts['média']]
pie.labels = ['Alta (1)', 'Média (1)']
pie.sideLabels = True
pie.slices[0].fillColor = colors.HexColor(PALETTE['alta'])
pie.slices[1].fillColor = colors.HexColor(PALETTE['média'])
pie.slices.strokeWidth = 0
donut.add(pie)
donut.add(Circle(97.5, 77.5, 34, fillColor=colors.white, strokeColor=None))
donut.add(String(97.5, 73, '2', textAnchor='middle', fontName='AuditBold', fontSize=20))
bars = Drawing(235, 175)
chart = VerticalBarChart()
chart.x, chart.y, chart.width, chart.height = 25, 25, 205, 125
chart.data = [[0, 2, 0, 0, 0]]
chart.categoryAxis.categoryNames = ['Isolam.', 'Perm.', 'IDOR', 'Segredos', 'XSS']
chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 2, 1
chart.bars[0].fillColor = colors.HexColor('#2563EB')
chart.categoryAxis.labels.fontSize = 7
chart.valueAxis.labels.fontSize = 7
bars.add(chart)
story.append(Table([[donut, bars]], colWidths=[8*cm, 8*cm]))
story.append(p('Rosca: severidade. Barras: categoria primária; ambos os achados são falhas de permissão/fronteira no servidor. Zero nas demais categorias significa nenhum achado confirmado, não segurança garantida.', 'SmallAudit'))
item('Verificação',
     '7 regressões reproduziram as falhas antes da correção. Depois: 196 testes backend focados, mais 56 de transação/retomada/memória e 24 testes frontend aprovados. Os grupos backend são distintos. Suíte integral não repetida.')
item('Limite do resultado',
     'Os controles não são autenticação multiusuário, sandbox de processos locais ou autorização para expor o serviço. A escuta deve continuar em loopback.')
story.append(PageBreak())

title('2. Achados detalhados')
rows = [[p('ID / severidade', 'WhiteAudit'), p('Arquivo:linha atual', 'WhiteAudit'), p('Descrição / estado', 'WhiteAudit')]]
for f in findings:
    locations = '\n'.join(f"{r['file']}:{r['line']}" for r in f['locations'])
    rows.append([Paragraph(f'{f["id"]}<br/><font color="{PALETTE[f["severity"]]}">{f["severity"].upper()}</font>', styles['BodyAudit']),
                 p(locations, 'SmallAudit'), p(f['title'] + '\nCORRIGIDO', 'SmallAudit')])
story.append(table(rows, [3*cm, 6*cm, 7*cm]))
story.append(p('As referências atuais apontam os locais de correção. As posições e trechos anteriores são identificados abaixo como baseline observado, sem confundi-los com linhas atuais.'))
for f in findings:
    story.append(PageBreak())
    title(f'{f["id"]} - {f["title"]}')
    story.append(Paragraph(f'<font color="{PALETTE[f["severity"]]}">SEVERIDADE {f["severity"].upper()}</font> | CORRIGIDO', styles['H2Audit']))
    item('Localização', '; '.join(f"{r['file']}:{r['line']}" for r in f['locations']))
    story.append(p(f['baseline'], 'SmallAudit'))
    item('Entrada e condição', f['entry'] + ' ' + f['condition'])
    item('Impacto e justificativa', f['impact'])
    story.append(p('Trecho mínimo do baseline observado', 'H2Audit'))
    lines = '\n'.join(part for line in f['before'].splitlines() for part in (wrap(line, 83, replace_whitespace=False) or ['']))
    story.append(XPreformatted(escape(lines), styles['CodeAudit']))
    item('Correção executada', f['correction'])
    item('Verificação e limite', f['tests'] + ' ' + f['caveat'])

story.append(PageBreak())
title('3. Cobertura por handler e categoria')
story.append(p('Todos os 20 handlers explícitos foram inventariados por AST, sem falhas de parse, e rastreados na análise. A matriz estruturada registra as cinco categorias por handler.'))
rows = [[p('Arquivo:linha / handler', 'WhiteAudit'), p('Método e rota', 'WhiteAudit'), p('Controle / resultado', 'WhiteAudit')]]
for h in coverage['handlers']:
    boundary = ('Fronteira local; sessão/SQLite; SEC-001/002 corrigidos'
                if h['file'] == 'api/main.py' else
                'Binding exato antes do accept; uma sessão/store' if h['file'].startswith('api/') else
                'Fronteira local; token nos cinco endpoints API')
    rows.append([p(f"{h['file']}:{h['line']}\n{h['handler']}", 'SmallAudit'),
                 p(f"{h['method']} {h['path']}", 'SmallAudit'), p(boundary, 'SmallAudit')])
story.append(table(rows, [6*cm, 5*cm, 5*cm]))
story.append(Spacer(1, .25*cm))
story.append(p('Inventário runtime adicional: GET/HEAD /openapi.json, /docs, /docs/oauth2-redirect e /redoc, mais mount /assets. Todos herdam a barreira do app principal. Groq/Luna montam a mesma factory B, sem handlers alternativos ocultos.'))
for label, result in [
    ('Isolamento de dono/tenant', 'Não aplicável como multi-tenant: um operador local confiável. Sessões/objetos são escopados em SQLite e B vincula sessão/store no servidor; não há isolamento por pessoa.'),
    ('Permissão no navegador/servidor', 'Sem gates de papel no frontend: role é acessibilidade, não auth. Duas causas confirmadas no servidor foram corrigidas.'),
    ('IDOR', 'IDs de sessão/operação foram rastreados em todos os handlers. Não foi criada causa duplicada por falta de owner_id num produto sem usuários; o vetor externo é SEC-001.'),
    ('Segredos embutidos', 'Varredura mascarada de código, histórico e bundle. 14 indicadores atuais classificados como fixtures de teste; zero indicadores no histórico pelos padrões usados. .env e credenciais fora da leitura.'),
    ('XSS', 'JSX renderiza texto, sem sink de HTML arbitrário encontrado; página offline usa textContent e token gerado pelo servidor. Testes com HTML malicioso passaram.'),
]:
    item(label, result)

story.append(PageBreak())
title('4. Pontos fortes, pontos fracos e limites')
for value in data['strengths']:
    story.append(Paragraph('<font color="#059669">PROTEGIDO</font> ' + escape(value), styles['BodyAudit']))
item('Pontos fracos observados',
     'A confiança no localhost não estava aplicada à origem do navegador no fluxo padrão; a classificação privada das fontes não era aplicada na resposta da consolidação. Ambas as causas foram corrigidas, sem autenticação nova ou migração.')
for value in data['limitations']:
    story.append(p('- ' + value))
item('Extensão do scan',
     f"{coverage['current_text_files_scanned']} arquivos textuais atuais; {coverage['historical_text_blobs_scanned']} blobs textuais históricos; {coverage['local_commits']} commits locais; clone não raso; bundle {', '.join(coverage['bundle_files'])}. Sem fetch remoto.")
story.append(PageBreak())
title('5. Recomendações priorizadas')
for recommendation in data['recommendations']:
    item(recommendation['priority'], recommendation['text'])
item('Reprodução',
     'Na raiz do worktree, executar scan_local.py com Python do projeto e gerar_relatorio.py com o runtime documental que contém reportlab/pypdf/pypdfium2. Os testes e comandos exatos estão em README.md nesta pasta.')
item('Aceitação',
     'O relatório confirma correções e testes locais, não aceita narrador, campanha, arquitetura nova ou release. Não há achado confirmado desta auditoria aguardando credencial ou decisão humana para correção.')

issue_blocks = []
for index, f in enumerate(findings, 1):
    lines = [f'--- ISSUE {index} ---',
             f'# [Segurança] {f["title"]}',
             f'Labels sugeridas: security, {f["severity"]}',
             'Estado: corrigido localmente; rascunho de rastreabilidade, não publicado.',
             '', '## Problema', f['entry'] + ' ' + f['condition'],
             '', '## Evidência', f['baseline'],
             *[f'- {r["file"]}:{r["line"]} (correção atual)' for r in f['locations']],
             '```python', f['before'], '```',
             '', '## Impacto', f['impact'],
             '', '## Correção recomendada / executada', f['correction'],
             '', '## Verificação', f['tests'],
             '', '## Critérios de aceite',
             *['- [x] ' + criterion for criterion in f['acceptance']],
             '', '## Limitações', f['caveat'], f'--- FIM ISSUE {index} ---']
    block = '\n'.join(lines).replace('\\`', '`')
    issue_blocks.append(block)
    story.append(PageBreak())
    title('ISSUES PARA O GITHUB')
    story.append(p(f'Rascunho {index} de {len(findings)}; nenhuma publicação executada. Texto Markdown completo abaixo.', 'SmallAudit'))
    for line in block.splitlines():
        story.append(p(line or ' ', 'SmallAudit'))
(HERE / 'issues.md').write_text('\n\n'.join(issue_blocks) + '\n', encoding='utf-8')
pdf = HERE / 'relatorio-auditoria-seguranca.pdf'
SimpleDocTemplate(str(pdf), pagesize=(21*cm, 29.7*cm), leftMargin=2*cm,
                  rightMargin=2*cm, topMargin=1.7*cm, bottomMargin=2*cm,
                  title='Relatório de Auditoria de Segurança - Agente Storyteller',
                  author='Codex - auditoria local').build(story, onFirstPage=footer, onLaterPages=footer)

from pypdf import PdfReader
reader = PdfReader(str(pdf))
text = '\n'.join(page.extract_text() or '' for page in reader.pages)
assert all(f['id'] in text for f in findings)
assert 'ISSUES PARA O GITHUB' in text and 'FIM ISSUE 2' in text
assert len(reader.pages) >= 6
surfaces = ['api/main.py', 'api/local_request_security.py',
            'scripts/run_campaign_source_offline_trial.py',
            'tests/test_security_audit_regressions.py', 'tests/conftest.py',
            'tests/test_campaign_source_offline_trial.py', 'tests/test_perf_sec.py',
            'client/src/components/NarrativeLog.test.tsx']
manifest = {'surfaces_sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in surfaces},
            'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
            'pages': len(reader.pages), 'findings': len(findings), 'corrected': len(findings)}
(HERE/'manifesto-auditoria.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw
previews = HERE/'previews'
previews.mkdir(exist_ok=True)
document = pdfium.PdfDocument(str(pdf))
thumbs = []
for number in range(len(document)):
    image = document[number].render(scale=1.2).to_pil().convert('RGB')
    image.save(previews/f'pagina-{number+1:02}.png')
    image.thumbnail((330, 480))
    tile = Image.new('RGB', (350, 510), 'white')
    tile.paste(image, ((350-image.width)//2, 20))
    ImageDraw.Draw(tile).text((12, 492), f'Pagina {number+1}', fill='black')
    thumbs.append(tile)
sheet = Image.new('RGB', (700, 510*((len(thumbs)+1)//2)), '#dce3eb')
for i, image in enumerate(thumbs):
    sheet.paste(image, ((i%2)*350, (i//2)*510))
sheet.save(previews/'visao-geral.png')
print(json.dumps({'pdf': str(pdf), 'pages': len(reader.pages), 'findings': len(findings), 'rendered_pages': len(thumbs)}, ensure_ascii=False))
