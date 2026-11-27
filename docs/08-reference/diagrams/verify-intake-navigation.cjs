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
    await page.goto(url('architecture/generated/HomelabSystemOverview.svg'));
    const fills=await page.locator('[data-model="SYS-intake"] > rect, [data-model="SYS-trust"] > rect').evaluateAll(nodes=>nodes.map(n=>getComputedStyle(n).fill));
    if(fills.length!==2||fills[0]!==fills[1])throw Error('Logical subsystem colour drift');
    for(const [selector,suffix] of [
      ['a:has(>[data-model="SYS-intake"])','software-intake/SoftwareIntakeLogicalDesign.svg'],
      ['a:has(>[data-model="L-Proxy"])','software-intake/solution/SoftwareIntakeSolutionDesign.svg'],
      ['a[aria-label="Use cases"]','software-intake/SoftwareIntakeUseCases.svg'],
      ['a[aria-label="Operator goal: Clone a Git repository over HTTPS"]','platform/hosting/Boot1CloneRepository.svg'],
      ['a:has(>[data-model="ACT-intake"])','software-intake/SoftwareIntakeLogicalDesign.svg'],
      ['[data-model="L-Cache"] > a','software-intake/solution/SoftwareIntakeSolutionDesign.svg'],
      ['a[aria-label="Logical design"]','software-intake/SoftwareIntakeLogicalDesign.svg'],
      ['a[aria-label="Proxy contract"]','policy-proxy/PolicyProxyContract.svg'],
      ['a[aria-label="Logical design"]','software-intake/SoftwareIntakeLogicalDesign.svg'],
      ['a[aria-label="Use cases"]','software-intake/SoftwareIntakeUseCases.svg'],
      ['a[data-model="SC-http-miss"]','SoftwareIntakeUseCases.svg#SC-http-miss'],
      ['[data-view="SC-http-miss"] a:has([data-element="L-Proxy"])','software-intake/solution/SoftwareIntakeSolutionDesign.svg'],
      ['a[aria-label="Use cases"]','software-intake/SoftwareIntakeUseCases.svg'],
      ['a[data-model="SC-http-miss"]','SoftwareIntakeUseCases.svg#SC-http-miss'],
      ['[data-view="SC-http-miss"] a[data-message="H-fetch"]','SoftwareIntakeFunctions.svg#F-http'],
      ['[data-view="F-http"] a:has([data-element="L-Proxy"])','software-intake/solution/SoftwareIntakeSolutionDesign.svg'],
      ['a[aria-label="Logical design"]','software-intake/SoftwareIntakeLogicalDesign.svg'],
    ]){
      await page.locator(selector).first().click();
      await page.waitForURL(u=>u.href.endsWith(suffix));report.journeys.push(suffix);
      if(suffix.endsWith('/solution/SoftwareIntakeSolutionDesign.svg')){
        if(await page.locator('svg').first().getAttribute('data-view-id')!=='VIEW-software-intake-placement')
          throw Error('Click reached a different solution view');
        if(await page.locator('[data-model^="RUN-"]').count()<1)throw Error('Solution lacks selected software');
      }
      if(suffix.endsWith('/Boot1CloneRepository.svg')){
        if(!await page.locator('[data-model="ACT-operator"] .actor-symbol').isVisible())
          throw Error('Human glyph is not visible on the actual clicked route');
      }
    }
    await page.goto(url('architecture/generated/HomelabUseCases.svg'));
    await page.locator('a:has(>[data-model="UC-clone"])').click();
    await page.waitForURL(u=>u.href.endsWith('/platform/hosting/Boot1CloneRepository.svg'));
    report.journeys.push('system goals â†’ boot-1 goal');
    await page.locator('a:has(>[data-model="ACT-intake"])').click();
    await page.waitForURL(u=>u.href.endsWith('/software-intake/SoftwareIntakeLogicalDesign.svg'));
    report.journeys.push('supporting intake actor â†’ intake design');
    const targets=["HomelabSystemOverview.svg", "HomelabUseCases.svg", "HomelabRequirements.md", "HomelabFunctions.svg", "software-intake/SoftwareIntakeLogicalDesign.svg", "software-intake/solution/SoftwareIntakeSolutionDesign.svg", "platform/SharedPlatformOverview.svg", "software-intake/solution/SoftwareIntakeResources.svg", "platform/hosting/Boot1CloneRepository.svg", "software-intake/SoftwareIntakeUseCases.svg", "software-intake/SoftwareIntakeRequirements.md", "software-intake/SoftwareIntakeFunctions.svg", "software-intake/SoftwareIntakeVerification.md"];
    for(const target of targets.filter(name=>name.endsWith('.svg'))){
      await page.goto(url("architecture/generated/"+target));
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
      if(target==='platform/hosting/Boot1CloneRepository.svg'){
        if(await page.locator('[data-model="ACT-operator"] .actor-symbol').count()!==1)
          throw Error('Human operator lost its actor glyph');
      }
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
  console.log(`Verified ${report.journeys.length} navigation steps and ${report.views.length} focused views; saved ${report.views.length*4} previews.`);
})().catch(e=>{console.error(e);process.exitCode=1});
