// Run from the upstream checkout with the documented Playwright/Edge setup.
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.DIAGRAM_PLAYWRIGHT||'playwright');

(async()=>{
  const output=path.resolve('.tmp/intake-focused');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const report={browser:browser.version(),journeys:[],views:[]};
  const url=name=>{const [file,fragment]=name.split('#');return pathToFileURL(path.resolve(file)).href+(fragment?'#'+fragment:'')};
  const page=await browser.newPage({viewport:{width:1100,height:1000}});
  try{
    await page.goto(url('architecture/views/system-overall.svg'));
    const fills=await page.locator('[data-model="SYS-intake"] > rect, [data-model="SYS-trust"] > rect').evaluateAll(nodes=>nodes.map(n=>getComputedStyle(n).fill));
    if(fills.length!==2||fills[0]!==fills[1])throw Error('Logical subsystem colour drift');
    for(const [selector,suffix] of [
      ['a:has(>[data-model="SYS-intake"])','software-intake/logical.svg'],
      ['a[aria-label="Use cases"]','software-intake/use-cases.svg'],
      ['a[data-model="SC-http-miss"]','scenario-views.svg#SC-http-miss'],
      ['[data-view="SC-http-miss"] a[data-message="H-fetch"]','function-views.svg#F-http'],
      ['[data-view="F-http"] a:has([data-element="L-Proxy"])','policy-proxy/contract.svg'],
      ['a[aria-label="Up to overview"]','software-intake/logical.svg'],
      ['a[aria-label="Requirements"]','software-intake/requirements.svg'],
      ['a[aria-label="Verification cases"]','software-intake/tests.svg#REQ-policy'],
      ['a:has(>[data-model="VC-http-hit"])','scenario-views.svg#SC-http-hit'],
    ]){
      await page.locator(selector).first().click();
      await page.waitForURL(u=>u.href.endsWith(suffix));report.journeys.push(suffix);
    }
    await page.goto(url('architecture/views/use-cases.svg'));
    await page.locator('a:has(>[data-model="UC-clone"])').click();
    await page.waitForURL(u=>u.href.endsWith('/platform/hosting/clone-repository.svg'));
    report.journeys.push('system goals → boot-1 goal');
    await page.locator('a:has(>[data-model="ACT-intake"])').click();
    await page.waitForURL(u=>u.href.endsWith('/software-intake/logical.svg'));
    report.journeys.push('supporting intake actor → intake design');
    const targets=['system-overall.svg','use-cases.svg','requirements.svg','functions.svg',
      'software-intake/logical.svg','software-intake/placement.svg','platform/overview.svg',
      'software-intake/use-cases.svg','software-intake/requirements.svg','software-intake/functions.svg',
      'software-intake/tests.svg'];
    for(const target of targets){
      await page.goto(url('architecture/views/'+target));
      const result=await page.evaluate(()=>{
        const svg=document.documentElement;
        const overflow=[];
        for(const group of svg.querySelectorAll('.model-node')){
          const box=group.querySelector('rect,ellipse')?.getBoundingClientRect();if(!box)continue;
          for(const label of group.querySelectorAll('text')){
            const b=label.getBoundingClientRect();
            if(b.left<box.left-2||b.right>box.right+2||b.top<box.top-2||b.bottom>box.bottom+2)overflow.push(label.textContent);
          }
        }
        if(svg.querySelector('[data-concern],.context-card'))throw Error('Retired context frame survived');
        return {svg:svg.outerHTML,overflow};
      });
      if(result.overflow.length)throw Error(target+': text overflow: '+result.overflow.join('; '));
      report.views.push({source:target,overflow:result.overflow});
      for(const width of [1100,760])for(const theme of ['light','dark']){
        const preview=await browser.newPage({viewport:{width,height:1100}});
        await preview.setContent(`<style>body{margin:20px;background:${theme==='light'?'#fff':'#0d1117'}}svg{display:block;width:100%;height:auto}main{background:white}</style><main>${result.svg}</main>`);
        await preview.locator('main').screenshot({path:path.join(output,target.replaceAll('/','-').replace('.svg','')+`-${width}-${theme}.png`)});
        await preview.close();
      }
    }
  }finally{await browser.close()}
  fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(`Verified ${report.journeys.length} navigation steps and ${report.views.length} focused views; saved 44 previews.`);
})().catch(e=>{console.error(e);process.exitCode=1});
