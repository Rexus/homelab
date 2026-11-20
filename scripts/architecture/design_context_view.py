"""Keep scoped model inspection as supporting data, without generating context dashboards."""

import json
from pathlib import Path
from design_context import INDEX, projections, relative


def context_outputs(root,model,records,plan,existing):
    outputs={}
    projected=projections(root,model,records,plan)
    for scope,data,_ in projected.values():
        path=Path(scope['page'])
        document=(root/path).read_text(encoding='utf-8')
        start='<!-- BEGIN DESIGN CONTEXT -->';end='<!-- END DESIGN CONTEXT -->'
        links=[]
        if scope['key'] in ('system','intake'):
            base='architecture/views/' + ('software-intake/' if scope['key']=='intake' else '')
            for label,name in [('Use cases','use-cases'),('Requirements','requirements'),('Functions','functions')]:
                links.append(f'[{label}]({relative(path,base+name+".svg")})')
            links.append(f'[Tests]({relative(path,"architecture/views/software-intake/tests.svg")})')
        else:
            links=[f'[Owning documentation]({relative(path,owner)})' for owner in scope['owners']]
        content='\n## Connected views\n\n'+' · '.join(links)+'.\n\n'+scope['coverage']+'\n'
        outputs[path]=document[:document.index(start)+len(start)]+content+document[document.index(end):]
    outputs[INDEX]=json.dumps({key:data for key,(_,data,_) in projected.items()},indent=2)+'\n'
    return outputs
