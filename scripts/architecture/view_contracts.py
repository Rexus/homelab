"""Boundary and change-impact renderings of the same reusable contract."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from diagram_notation import tag
from svg_pages import page, card, finish, text, link

BASE = Path('architecture/views/software-intake/policy-proxy')


def contract_outputs(root, model):
    config = json.loads((root/'architecture/views/syson.json').read_text())
    key = config['contract']
    definition = model['elements'][key]
    ports = definition['ports']
    path = (BASE/'contract.svg').as_posix()
    svg, y, nav = page(path, 'Policy proxy contract', config['contract_question'],
                      'architecture/design/software-intake/policy-proxy/README.md', 'architecture/views/software-intake/logical.svg')
    svg.set('data-view-id', 'VIEW-proxy-contract')
    svg.set('data-subject', key)
    svg.set('data-contract-documentation', config['contract_documentation'])
    svg.set('data-contract-ports', json.dumps(ports))
    y += card(svg, path, 30, y, 900, key+' · '+definition['name'], ' '.join(definition['docs']), key=key) + 20
    text(svg, 'Owned interfaces', 30, y+20, 18, weight='bold')
    y += 36
    for port in ports:
        y += card(svg, path, 30, y, 900, port, 'TransferPort') + 12
    nav[2] = ('Change impact', (BASE/'change-impact.svg').as_posix())
    outputs = {Path(path): ET.tostring(finish(svg,path,y,nav),encoding='unicode')+'\n'}
    path = (BASE/'change-impact.svg').as_posix()
    consumers = sorted(e['from'] for e in model['edges'] if e['kind']=='typed-by' and e['to']==key)
    relations = [e for e in model['edges'] if e['kind']=='typed-by' and e['to']==key and e['from'] in consumers]
    svg,y,nav=page(path,'Proxy change impact — typed uses',config['impact_question'],
                   'architecture/design/software-intake/policy-proxy/README.md','architecture/views/software-intake/logical.svg')
    svg.set('data-view-id','VIEW-proxy-impact');svg.set('data-subject',key)
    svg.set('data-relationships',json.dumps(relations))
    y += card(svg,path,30,y,900,key+' · '+definition['name'],'Reusable contract', (BASE/'contract.svg').as_posix(),key)+20
    for consumer in consumers:
        e=model['elements'][consumer]
        y += card(svg,path,30,y,900,consumer+' · '+e['name'], 'Typed by '+key+' · '+definition['name'],key=consumer)+12
    nav[2]=('Contract',(BASE/'contract.svg').as_posix())
    outputs[Path(path)] = ET.tostring(finish(svg,path,y,nav),encoding='unicode')+'\n'
    return outputs
