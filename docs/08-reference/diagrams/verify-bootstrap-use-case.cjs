const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.DIAGRAM_PLAYWRIGHT);
(async () => {
  const file = path.resolve('architecture/views/platform/hosting/clone-repository.svg');
  const output = path.resolve('.tmp/intake-render');
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const report = {previews:[],journey:[]};
  try {
    for (const width of [1100,760]) for (const theme of ['light','dark']) {
      const page = await browser.newPage({viewport:{width,height:720}});
      await page.setContent(`<style>body{margin:20px;background:${theme==='light'?'#fff':'#0d1117'}}svg{display:block;width:100%;height:auto}</style>` + fs.readFileSync(file,'utf8'));
      const overflow = await page.locator('svg').evaluate(svg => {
        const result = [], bounds = svg.getBoundingClientRect();
        for (const text of svg.querySelectorAll('text')) {
          const b = text.getBoundingClientRect();
          if (b.left < bounds.left || b.right > bounds.right || b.top < bounds.top || b.bottom > bounds.bottom) result.push(text.textContent);
        }
        for (const g of svg.querySelectorAll('g[data-model]')) {
          const shape = g.querySelector('rect');
          if (!shape) continue;
          const b = shape.getBoundingClientRect();
          for (const t of g.querySelectorAll('text')) {
            const r=t.getBoundingClientRect();
            if (r.left<b.left || r.right>b.right || r.top<b.top || r.bottom>b.bottom) result.push(g.getAttribute('data-model'));
          }
        }
        return result;
      });
      if (overflow.length) throw Error(JSON.stringify(overflow));
      await page.locator('svg').screenshot({path:path.join(output,`boot-clone-${width}-${theme}.png`)});
      report.previews.push({width,theme,overflow});
      await page.close();
    }
    const page = await browser.newPage({viewport:{width:1100,height:1000}});
    await page.goto(pathToFileURL(file).href);
    await page.locator('a:has(g[data-model="UC-clone-host"])').click({position:{x:220,y:30}});
    await page.waitForURL(u=>u.pathname.endsWith('/hosting/bootstrap-reference.svg'));
    if (await page.locator('g[data-model="BOOT-host"]').count() !== 1) throw Error('Wrong foundation host');
    await page.screenshot({path:path.join(output,'bootstrap-foundation.png'),fullPage:false,animations:'disabled'});
    report.journey.push('boot-1 subject → same host in foundation reference');
    await page.locator('a[aria-label="Clone use case"]').click();
    await page.waitForURL(u=>u.pathname.endsWith('/hosting/clone-repository.svg'));
    report.journey.push('foundation reference → originating use case');
    await page.locator('a:has(g[data-model="ACT-intake"])').click();
    await page.waitForURL(u=>u.pathname.endsWith('/software-intake/logical.svg'));
    report.journey.push('supporting software intake actor → separate logical design');
    await page.goBack();
    await page.locator('a[aria-label="HTTPS behavior"]').click();
    await page.waitForURL(u=>u.href.endsWith('scenario-views.svg#SC-https'));
    report.journey.push('bootstrap use case → existing expected HTTPS behavior');
  } finally {await browser.close();}
  fs.writeFileSync(path.join(output,'boot-clone-browser-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exit(1)});
