"""Evaluate the SysML admission expressions with the native engine, not a second Python model."""

import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from intake_sources import require


def evaluate(root,args):
    from software_intake import run
    run(root,'build',args)
    work=root/'.tmp/software-intake-analysis'
    work.mkdir(parents=True,exist_ok=True)
    queries={}
    inputs={}
    for values in itertools.product((False,True),repeat=4):
        key=''.join('1' if x else '0' for x in values)
        literal=', '.join(str(v).lower() for v in values)
        inputs[key]=dict(zip(('clientAllowed','destinationAllowed','portAllowed','cacheHit'),values))
        queries[key+'-policy']='SoftwareIntake::AdmissionLogic::AdmissionAllowed('+', '.join(str(v).lower() for v in values[:3])+')'
        queries[key+'-candidate']='CacheShortcut('+literal+')'
        queries[key+'-counterexample']="AdmissionOrderReview(SoftwareIntake::Context::context.'Policy proxy / HTTP cache', "+literal+')'
    (work/'queries.json').write_text(json.dumps(queries,indent=2)+'\n',encoding='utf-8')
    source=root/'.tmp/software-intake-model/combined.sysml'
    result=subprocess.run([args.java,'-cp',args.kernel,str(root/'scripts/architecture/EvaluateModel.java'),
        args.library,str(source),str(work/'queries.json'),str(work/'answers.json')],capture_output=True,text=True,encoding='utf-8',timeout=120)
    (work/'evaluation.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    require(result.returncode==0,'Native expression evaluation failed; inspect '+str(work/'evaluation.log'))
    answers=json.loads((work/'answers.json').read_text())
    rows=[{'inputs':v,'policy_admits':answers[k+'-policy'],'candidate_admits':answers[k+'-candidate'],'counterexample':answers[k+'-counterexample']} for k,v in inputs.items()]
    report={'analysis':'AN-admission','engine':'SysML Pilot 0.63.1 native expression evaluator',
        'scope':'Boolean admission predicates only; not timing, protocol execution or deployed behavior',
        'model_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'rows':rows,'counterexamples':[r for r in rows if r['counterexample']]}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"Evaluated {len(rows)} combinations; candidate violates policy in {len(report['counterexamples'])}.")
    print('Result: '+str(work/'result.json'))
    return report
