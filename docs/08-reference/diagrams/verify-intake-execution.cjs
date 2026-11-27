const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');
(async () => {
  const folder = path.resolve('.tmp/intake-render'); fs.mkdirSync(folder, {recursive:true});
  const file = 'architecture/generated/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.svg';
  const url = id => pathToFileURL(path.resolve(file)).href + (id ? '#' + id : '');
  const browser = await chromium.launch({channel:'msedge', headless:true});
  const report = {browser:browser.version(), views:[], journey:[]};
  try {
    const p = await browser.newPage({viewport:{width:1100,height:1400}});
    await p.goto(url());
    const ids = await p.locator('svg > view').evaluateAll(nodes => nodes.map(n => n.id));
    if (ids.length !== 7) throw new Error('Missing native run views');
    for (const id of ids) {
      await p.goto(url(id));
      const result = await p.evaluate(id => {
        const active = document.querySelector(`svg[data-view="${id}"]`);
        if (getComputedStyle(active).visibility !== 'visible') throw new Error('Hidden view');
        const overflow = [];
        for (const g of active.querySelectorAll('.explorer-card')) {
          const b = g.querySelector('rect').getBoundingClientRect();
          for (const t of g.querySelectorAll('text')) {
            const r = t.getBoundingClientRect();
            if (r.left < b.left-1 || r.right > b.right+1 || r.top < b.top-1 || r.bottom > b.bottom+1) overflow.push(t.textContent);
          }
        }
        const messages = [...active.querySelectorAll('[data-execution]')].map(n => n.dataset.message);
        const clone = active.cloneNode(true);
        for (const a of ['x','y','width','height','data-view']) clone.removeAttribute(a);
        return {svg:clone.outerHTML, overflow, messages};
      }, id);
      if (result.overflow.length) throw new Error(JSON.stringify(result.overflow));
      if (id !== 'index' && result.messages.length === 0) throw new Error('Missing observed messages');
      if (id === 'RUN-source-failure' && (result.messages.includes('H-verify') || !result.messages.includes('H-unavailable'))) throw new Error('Incorrect failure trace');
      if (id === 'RUN-hit-offline' && (result.messages.includes('H-fetch') || !result.messages.includes('H-verify'))) throw new Error('Incorrect cache trace');
      report.views.push({id,messages:result.messages});
      for (const width of [1100,760]) for (const theme of ['light','dark']) {
        const preview = await browser.newPage({viewport:{width,height:1400}});
        await preview.setContent(`<style>body{margin:20px;background:${theme==='light'?'#fff':'#0d1117'}}main>svg{display:block;width:100%;height:auto}main{background:white}</style><main>${result.svg}</main>`);
        await preview.locator('main').screenshot({path:path.join(folder,`execution-${id}-${width}-${theme}.png`)});
        await preview.close();
      }
    }
    await p.goto(url());
    await p.locator('[data-view="index"] a[href="execution.svg#RUN-source-failure"]').click();
    await p.waitForURL(u => u.href.endsWith('#RUN-source-failure')); report.journey.push('execution index → observed failure');
    await p.locator('[data-view="RUN-source-failure"] a[data-message="H-fetch"]').click();
    await p.waitForURL(u => u.href.endsWith('function-views.svg#F-http')); report.journey.push('observed fetch → function');
    await p.goBack();
    await p.locator('[data-view="RUN-source-failure"] a[href="scenario-views.svg#SC-http-source-failure"]').click();
    await p.waitForURL(u => u.href.endsWith('scenario-views.svg#SC-http-source-failure')); report.journey.push('observed → expected failure');
    await p.locator('[data-view="SC-http-source-failure"] a[href="execution.svg"]').click();
    await p.waitForURL(u => u.href.endsWith('execution.svg')); report.journey.push('expected → execution index');
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(folder,'execution-browser-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(`Passed ${report.views.length} execution views, ${report.journey.length} navigation steps and 28 previews.`);
})().catch(e=>{console.error(e);process.exitCode=1});
