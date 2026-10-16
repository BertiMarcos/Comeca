# -*- coding: utf-8 -*-
"""Genera data/files/femape_cuota_social.osheet.json — tercer tablero de FEMAPE.

Metodo: se clona la plantilla (Ingresos y Egresos) para heredar styles, formats,
settings y el id del filtro global, y se escriben hojas, pivots y figuras nuevas,
con assert sobre todo lo que se da por cierto de la plantilla.

Claves que se confunden solo (ver estado-tableros-femape):
  cells/styles/formats/merges/dataRange/labelRange -> notacion A1, base UNO
  rows/cols/figures (col,row)                      -> indices base CERO
"""
import json, os, re, uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(AQUI, 'data', 'files', 'femape_ingresos_egresos.osheet.json')
SALIDA = os.path.join(AQUI, 'data', 'files', 'femape_cuota_social.osheet.json')

PRODUCTO_CUOTA = 10          # 4016-Cuotas Sociales, cuenta de ingreso 6100000

t = json.load(open(PLANTILLA, encoding='utf-8'))
assert t['version'] == '18.5.10', t['version']
assert set(t['styles']) == {'1', '2', '3', '4', '5', '6'}, t['styles']
assert t['formats']['1'] == '#,##0' and t['formats']['2'] == '0.0%'
assert len(t['globalFilters']) == 1 and t['globalFilters'][0]['type'] == 'date'
assert [s['name'] for s in t['sheets']] == ['Tablero', 'Data']
FILTRO = t['globalFilters'][0]['id']

SH_TAB = str(uuid.uuid4())
SH_DAT = str(uuid.uuid4())
fecha = {FILTRO: {'chain': 'invoice_date', 'type': 'date', 'offset': 0}}

POSTED = ['&', '&', ['state', '=', 'posted'], ['move_type', '=', 'out_invoice'],
          ['invoice_line_ids.product_id', '=', PRODUCTO_CUOTA]]
IMPAGAS = ['&'] + POSTED + [['payment_state', 'in', ['not_paid', 'partial']]]

pivots = {
    '1': {'type': 'ODOO', 'model': 'account.move', 'name': 'Cuota social por mes',
          'id': '1', 'formulaId': '1', 'context': {}, 'domain': POSTED,
          'fieldMatching': fecha, 'sortedColumn': None, 'columns': [],
          'rows': [{'fieldName': 'invoice_date', 'granularity': 'month'}],
          'measures': [{'id': '__count', 'fieldName': '__count'},
                       {'id': 'amount_untaxed_signed', 'fieldName': 'amount_untaxed_signed',
                        'userDefinedName': 'Importe'}]},
    '2': {'type': 'ODOO', 'model': 'res.partner', 'name': 'Socios por estado',
          'id': '2', 'formulaId': '2', 'context': {},
          'domain': [['customer_rank', '>', 0]], 'fieldMatching': {},
          'sortedColumn': {'measure': '__count', 'order': 'desc', 'domain': []},
          'columns': [], 'rows': [{'fieldName': 'x_studio_estado_socio'}],
          'measures': [{'id': '__count', 'fieldName': '__count',
                        'userDefinedName': 'Socios'}]},
    '3': {'type': 'ODOO', 'model': 'account.move', 'name': 'Los que mas deben',
          'id': '3', 'formulaId': '3', 'context': {}, 'domain': IMPAGAS,
          'fieldMatching': fecha,
          'sortedColumn': {'measure': 'amount_residual_signed', 'order': 'desc',
                           'domain': []},
          'columns': [], 'rows': [{'fieldName': 'partner_id'}],
          'measures': [{'id': 'amount_residual_signed',
                        'fieldName': 'amount_residual_signed',
                        'userDefinedName': 'Debe'}]},
    '4': {'type': 'ODOO', 'model': 'account.move', 'name': 'KPI - pendiente de cobro',
          'id': '4', 'formulaId': '4', 'context': {}, 'domain': IMPAGAS,
          'fieldMatching': fecha, 'sortedColumn': None, 'columns': [], 'rows': [],
          'measures': [{'id': '__count', 'fieldName': '__count'},
                       {'id': 'amount_residual_signed',
                        'fieldName': 'amount_residual_signed'}]},
}

MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

def plata(ref):
    return ('=CONCATENATE(IF(%s<0,"-$","$"),TEXT(ABS(%s)/1000000,"#,##0.0")," M")'
            % (ref, ref))

dat = {
    'A1': 'Anio del filtro', 'B1': '=YEAR(ODOO.FILTER.VALUE("Periodo"))',
    'A2': 'Facturas emitidas', 'B2': '=IFERROR(PIVOT.VALUE(1,"__count"),0)',
    'C2': '=TEXT(B2,"#,##0")', 'D2': '=CONCATENATE("anio ",B1)',
    'A3': 'Importe facturado',
    'B3': '=IFERROR(PIVOT.VALUE(1,"amount_untaxed_signed"),0)',
    'C3': plata('B3'),
    'D3': '=CONCATENATE("$",TEXT(IFERROR(B3/B2,0),"#,##0")," promedio por factura")',
    'A4': 'Pendiente de cobro',
    'B4': '=IFERROR(PIVOT.VALUE(4,"amount_residual_signed"),0)',
    'C4': plata('B4'),
    'D4': '=CONCATENATE(TEXT(B5,"#,##0")," facturas impagas")',
    'A5': 'Facturas impagas', 'B5': '=IFERROR(PIVOT.VALUE(4,"__count"),0)',
    'A6': 'Socios Normal',
    'B6': '=IFERROR(PIVOT.VALUE(2,"__count","x_studio_estado_socio","Normal"),0)',
    'C6': '=TEXT(B6,"#,##0")', 'D6': 'con cuota social activa',
    'A7': 'Socios Suspendidos',
    'B7': '=IFERROR(PIVOT.VALUE(2,"__count","x_studio_estado_socio","Suspendido"),0)',
    'C7': '=CONCATENATE(TEXT(B7,"#,##0")," / ",TEXT(B9,"#,##0"))',
    'D7': 'suspendidos / en tramite',
    'A8': 'Socios de Baja',
    'B8': '=IFERROR(PIVOT.VALUE(2,"__count","x_studio_estado_socio","Baja"),0)',
    'C8': '=TEXT(B8,"#,##0")',
    'D8': '=CONCATENATE(TEXT(IFERROR(B8/(B6+B7+B8+B9),0)*100,"#,##0.0"),"% del padron")',
    'A9': 'Socios En tramite',
    'B9': '=IFERROR(PIVOT.VALUE(2,"__count","x_studio_estado_socio"," En tramite"),0)',
    'A11': 'mes', 'B11': 'importe', 'C11': 'facturas', 'D11': 'etiqueta',
}
for i, m in enumerate(MESES, start=1):
    f = 11 + i
    dat['A%d' % f] = '="%02d/"&$B$1' % i
    dat['B%d' % f] = ('=IFERROR(PIVOT.VALUE(1,"amount_untaxed_signed",'
                      '"invoice_date:month",A%d),0)' % f)
    dat['C%d' % f] = ('=IFERROR(PIVOT.VALUE(1,"__count",'
                      '"invoice_date:month",A%d),0)' % f)
    dat['D%d' % f] = m
dat['A25'] = 'Control: suma de los meses vs total'
dat['B25'] = '=SUM(B12:B23)'
dat['C25'] = '=IF(ABS(B25-B3)<0.5,"cuadra","REVISAR")'

tab = {
    'A1': 'Cuota Social',
    'A12': 'Cuota social facturada por mes',
    'A27': 'Socios por estado', 'A28': '=PIVOT(2,6,FALSE,FALSE)',
    'E27': 'Los que mas deben', 'E28': '=PIVOT(3,10,FALSE,FALSE)',
    'A40': 'Mes a mes', 'A41': 'Mes', 'B41': 'Importe', 'C41': 'Facturas',
    'A55': ('Nota: el filtro Periodo de este tablero toma solo el ANIO. Las facturas '
            'son las que llevan el producto 4016-Cuotas Sociales (cuenta 6100000). '
            '"Pendiente de cobro" es el residual de HOY, no el del cierre de cada mes.'),
}
for i, m in enumerate(MESES, start=1):
    f = 41 + i
    tab['A%d' % f] = '=Data!D%d' % (11 + i)
    tab['B%d' % f] = '=Data!B%d' % (11 + i)
    tab['C%d' % f] = '=Data!C%d' % (11 + i)
tab['A54'] = 'Total'
tab['B54'] = '=SUM(B42:B53)'
tab['C54'] = '=SUM(C42:C53)'

def sc(titulo, key, base, col, row, x, y, fondo):
    i = str(uuid.uuid4())
    return {'id': i, 'width': 320, 'height': 109, 'tag': 'chart',
            'data': {'baselineColorDown': '#DC6965', 'baselineColorUp': '#00A04A',
                     'baselineMode': 'text',
                     'title': {'text': titulo, 'color': '#434343', 'bold': True},
                     'type': 'scorecard', 'background': fondo,
                     'baseline': base, 'baselineDescr': {'text': ''},
                     'keyValue': key, 'humanize': False, 'chartId': i},
            'offset': {'x': x, 'y': y}, 'col': col, 'row': row}

AZUL, ROJO, VERDE = '#EFF6FF', '#FEF2F2', '#F0FDF4'
# Una tarjeta mide 109 px y el paso vertical entre filas apiladas es 119 px.
# Anclar en la fila 1 (base cero) deja libre la fila del titulo.
PASO = 119
figs = [
    sc('Facturas emitidas', 'Data!C2', 'Data!D2', 0, 1, 0, 0, AZUL),
    sc('Importe facturado', 'Data!C3', 'Data!D3', 0, 1, 340, 0, AZUL),
    sc('Pendiente de cobro', 'Data!C4', 'Data!D4', 0, 1, 680, 0, ROJO),
    sc('Socios Normal', 'Data!C6', 'Data!D6', 0, 1, 0, PASO, VERDE),
    sc('Suspendidos', 'Data!C7', 'Data!D7', 0, 1, 340, PASO, AZUL),
    sc('Socios de Baja', 'Data!C8', 'Data!D8', 0, 1, 680, PASO, ROJO),
]
g = str(uuid.uuid4())
figs.append({'id': g, 'width': 1000, 'height': 300, 'tag': 'chart',
             'data': {'type': 'bar',
                      'title': {'text': ''},
                      'background': '#FFFFFF', 'legendPosition': 'none',
                      'stacked': False, 'aggregated': False,
                      'dataSetsHaveTitle': False, 'verticalAxisPosition': 'left',
                      'dataSets': [{'dataRange': 'Data!B12:B23', 'label': 'Facturado'}],
                      'labelRange': 'Data!D12:D23', 'chartId': g},
             'offset': {'x': 0, 'y': 0}, 'col': 0, 'row': 13})

def hoja(sid, nombre, cells, ncol, nrow, cols, rows, figuras, estilos, formatos, merges):
    return {'id': sid, 'name': nombre, 'colNumber': ncol, 'rowNumber': nrow,
            'rows': rows, 'cols': cols, 'merges': merges, 'cells': cells,
            'styles': estilos, 'formats': formatos, 'borders': {},
            'conditionalFormats': [], 'dataValidationRules': [],
            'figures': figuras, 'tables': [], 'areGridLinesVisible': False,
            'isVisible': True, 'headerGroups': {'ROW': [], 'COL': []}, 'comments': {}}

sheets = [
    hoja(SH_TAB, 'Tablero', tab, 7, 60,
         {'0': {'size': 240}, '1': {'size': 190}, '2': {'size': 100},
          '3': {'size': 15}, '4': {'size': 240}, '5': {'size': 190},
          '6': {'size': 100}},
         {'11': {'size': 40}, '26': {'size': 40}, '39': {'size': 40},
          '53': {'size': 30}},
         figs,
         # OJO: el esquema es {rango: id_de_estilo}, NO {id: rango}, y la clave
         # tiene que ser UN rango (una coma rompe toZone: "unbounded ranges").
         {'A1': 1, 'A12': 2, 'A27': 2, 'E27': 2, 'A40': 2,
          'A41:C41': 3, 'A42:C53': 4, 'A54:C54': 3, 'A55:G57': 6},
         {'B42:C54': 1}, ['A55:G57']),
    hoja(SH_DAT, 'Data', dat, 8, 40, {'0': {'size': 220}}, {}, [],
         {'A1:D1': 2, 'A11:D11': 2},
         {'B2:B9': 1, 'B12:C23': 1, 'B25': 1}, []),
]

out = {'version': t['version'], 'sheets': sheets,
       'styles': t['styles'], 'formats': t['formats'], 'borders': {},
       'revisionId': str(uuid.uuid4()), 'uniqueFigureIds': True,
       'settings': t['settings'], 'pivots': pivots, 'pivotNextId': 5,
       'customTableStyles': {},
       'globalFilters': [{'id': FILTRO, 'type': 'date', 'label': 'Periodo',
                          'defaultValue': 'this_year'}],
       'lists': {}, 'listNextId': 1, 'chartOdooMenusReferences': {}}

# --- controles antes de escribir ---
refs = set()
for c in list(tab.values()) + list(dat.values()):
    if isinstance(c, str) and c.startswith('='):
        refs |= set(re.findall(r'Data!(\$?[A-Z]+\$?\d+)', c))
faltan = [r for r in refs if r.replace('$', '') not in dat]
assert not faltan, 'referencias a Data que no existen: %s' % sorted(faltan)
for f in figs:
    for k in ('keyValue', 'baseline'):
        v = f['data'].get(k)
        if v and v.startswith('Data!'):
            assert v.split('!')[1] in dat, 'figura apunta a %s inexistente' % v
    for ds in f['data'].get('dataSets', []):
        r = ds.get('dataRange', '')
        if r.startswith('Data!'):
            ini = r.split('!')[1].split(':')[0]
            assert ini in dat, 'grafico apunta a %s inexistente' % r
RANGO = re.compile(r'^\$?[A-Z]{1,3}\$?\d+(:\$?[A-Z]{1,3}\$?\d+)?$')
for h in sheets:
    for mapa, nom in ((h['styles'], 'styles'), (h['formats'], 'formats')):
        for k, v in mapa.items():
            assert RANGO.match(k), 'hoja %s: %s["%s"] no es un rango acotado' % (
                h['name'], nom, k)
            assert isinstance(v, int), 'hoja %s: %s["%s"] tiene que ser el id (int)' % (
                h['name'], nom, k)
    for m in h['merges']:
        assert RANGO.match(m), 'merge invalido: %s' % m

ids = [f['id'] for f in figs]
assert len(ids) == len(set(ids)), 'ids de figura repetidos'
for p in pivots.values():
    assert p['id'] == p['formulaId']
    for m in p['measures']:
        assert m['id'] and m['fieldName']

json.dump(out, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False)
print('escrito:', SALIDA, os.path.getsize(SALIDA), 'bytes')
print('pivots:', len(pivots), '| figuras:', len(figs),
      '| celdas Tablero:', len(tab), '| celdas Data:', len(dat))
print('controles: todas las referencias a Data existen; ids de figura unicos')
