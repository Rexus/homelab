const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');
(async () => {
  const folder = path.resolve('.tmp/intake-render');
  const base = 'architecture/generated/software-intake/';
  const url = file => { const [name, fragment] = file.split('#'); return pathToFileURL(path.resolve(base + name)).href + (fragment ? '#' + fragment : ''); };
  const browser = await chromium.launch({channel:'msedge', headless:true});
  const report = {browser:browser.version(), views:[], journey:[]};
  try {
    const page = await browser.newPage({viewport:{width:1100,height:1300}});
    for (const [name, file, id] of [
      ['product','implementation.svg','index'],
      ['readable-scenario','scenario-views.svg#SC-http-miss','SC-http-miss'],
      ['readable-function','function-views.svg#F-http','F-http']]) {
      await page.goto(url(file));
      const result = await page.evaluate(id => {
        const selected = document.querySelector(`svg[data-view="${id}"]`);
        if (!selected || getComputedStyle(selected).visibility !== 'visible') throw new Error('Missing active view');
        const overflow = [];
        for (const card of selected.querySelectorAll('.explorer-card')) {
          const rect = card.querySelector('rect').getBoundingClientRect();
          for (const text of card.querySelectorAll('text')) {
            const b = text.getBoundingClientRect();
            if (b.left < rect.left-1 || b.right > rect.right+1 || b.top < rect.top-1 || b.bottom > rect.bottom+1) overflow.push(text.textContent);
          }
        }
        const clone = selected.cloneNode(true);
        for (const a of ['x','y','width','height','data-view']) clone.removeAttribute(a);
        return {svg:clone.outerHTML, overflow};
      }, id);
      if (result.overflow.length) throw new Error(JSON.stringify(result.overflow));
      if (name === 'product' && !result.svg.includes('Squid: cache hit')) throw new Error('No current product evidence');
      report.views.push(name);
      for (const width of [1100,760]) for (const theme of ['light','dark']) {
        const preview = await browser.newPage({viewport:{width,height:1300}});
        await preview.setContent(`<style>body{margin:20px;background:${theme==='light'?'#fff':'#0d1117'}}main>svg{display:block;width:100%;height:auto}main{background:white}</style><main>${result.svg}</main>`);
        await preview.locator('main').screenshot({path:path.join(folder,`${name}-${width}-${theme}.png`)});
        await preview.close();
      }
    }
    await page.goto(url('implementation.svg'));
    await page.locator('[data-view="index"] a[href="scenario-views.svg#SC-http-cache-untrusted"]').click();
    await page.waitForURL(u => u.href.endsWith('#SC-http-cache-untrusted'));
    report.journey.push('real cached rejection → expected scenario');
    await page.locator('[data-view="SC-http-cache-untrusted"] a[data-message="H-verify"]').click();
    await page.waitForURL(u => u.href.endsWith('function-views.svg#F-verify'));
    report.journey.push('expected verification → client responsibility');
    await page.goBack();
    await page.locator('[data-view="SC-http-cache-untrusted"] a[href="implementation.svg"]').click();
    await page.waitForURL(u => u.href.endsWith('implementation.svg'));
    report.journey.push('expected scenario → product comparison');
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(folder,'product-browser-report.json'), JSON.stringify(report,null,2)+'\n');
  console.log('Passed 3 views, 3 navigation steps and 12 light/dark previews.');
})().catch(error => { console.error(error); process.exitCode=1; });
