const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');
(async () => {
  const folder=path.resolve('.tmp/intake-render'); fs.mkdirSync(folder,{recursive:true});
  const file='architecture/views/software-intake/engineering.svg';
  const url=id=>pathToFileURL(path.resolve(file)).href+(id?'#'+id:'');
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const report={browser:browser.version(),views:[],journey:[]};
  try {
    const p=await browser.newPage({viewport:{width:1100,height:1200}});
    await p.goto(url());
    const ids=await p.locator('svg > view').evaluateAll(nodes=>nodes.map(n=>n.id));
    for(const id of ids){
      await p.goto(url(id));
      const result=await p.evaluate(id=>{
        const active=document.querySelector(`svg[data-view="${id}"]`);
        if(getComputedStyle(active).visibility!=='visible')throw new Error('Hidden view');
        const overflow=[];
        for(const g of active.querySelectorAll('.explorer-card')){
          const b=g.querySelector('rect').getBoundingClientRect();
          for(const t of g.querySelectorAll('text')){
            const r=t.getBoundingClientRect();
            if(r.left<b.left-1||r.right>b.right+1||r.top<b.top-1||r.bottom>b.bottom+1)overflow.push(t.textContent);
          }
        }
        const clone=active.cloneNode(true);
        for(const a of ['x','y','width','height','data-view'])clone.removeAttribute(a);
        return {svg:clone.outerHTML,overflow,edges:active.querySelectorAll('.edge').length};
      },id);
      if(result.overflow.length)throw new Error(JSON.stringify(result.overflow));
      if(!result.edges)throw new Error('Missing native relationships');
      report.views.push({id,edges:result.edges});
      for(const width of [1100,760])for(const theme of ['light','dark']){
        const preview=await browser.newPage({viewport:{width,height:1200}});
        await preview.setContent(`<style>body{margin:20px;background:${theme==='light'?'#fff':'#0d1117'}}main>svg{display:block;width:100%;height:auto}main{background:white}</style><main>${result.svg}</main>`);
        await preview.locator('main').screenshot({path:path.join(folder,`engineering-${id}-${width}-${theme}.png`)});
        await preview.close();
      }
    }
    await p.goto(url());
    await p.locator('[data-view="relationships"] g.node a[href="engineering.svg#REQ-policy"]').click();
    await p.waitForURL(u=>u.href.endsWith('#REQ-policy'));report.journey.push('requirement → verification');
    await p.goBack();
    await p.locator('[data-view="relationships"] g.node a[href="function-views.svg#F-admit"]').click();
    await p.waitForURL(u=>u.href.endsWith('function-views.svg#F-admit'));report.journey.push('function → design context');
    await p.goto(url('REQ-egress'));
    if(!(await p.locator('[data-view="REQ-egress"]').textContent()).includes('No satisfaction assertion'))throw new Error('Missing gap');
  }finally{await browser.close();}
  fs.writeFileSync(path.join(folder,'engineering-browser-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(`Passed ${report.views.length} engineering views, ${report.journey.length} navigation steps and 20 previews.`);
})().catch(e=>{console.error(e);process.exitCode=1});
