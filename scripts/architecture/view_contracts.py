"""Boundary and change-impact renderings of the same reusable contract."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from diagram_notation import tag
from svg_pages import page, card, finish, text, link

BASE = Path('architecture/generated/software-intake/policy-proxy')


def contract_outputs(root, model):
    config = json.loads((root/'scripts/architecture/config/views/syson.json').read_text())
    key = config['contract']
    definition = model['elements'][key]
    ports = definition['ports']
    path = (BASE/'PolicyProxyContract.svg').as_posix()
    svg, y, nav = page(path, 'Policy proxy contract', config['contract_question'],
                      'architecture/models/software-intake/policy-proxy/PolicyProxy.sysml', 'architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg')
    svg.set('data-view-id', 'VIEW-proxy-contract')
    svg.set('data-subject', key)
    svg.set('data-contract-documentation', config['contract_documentation'])
    svg.set('data-contract-ports', json.dumps(ports))
    y += card(svg, path, 30, y, 900, key+' · '+definition['name'], ' '.join(definition['docs']), key=key) + 20
    text(svg, 'Owned interfaces', 30, y+20, 18, weight='bold')
    y += 36
    for port in ports:
        y += card(svg, path, 30, y, 900, port, 'TransferPort') + 12
    nav[2] = ('Implementation trace', 'artifacts/architecture/generated/software-intake/reverse-trace.md')
    outputs = {Path(path): ET.tostring(finish(svg,path,y,nav),encoding='unicode')+'\n'}
    return outputs
