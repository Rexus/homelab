// From the repository root, use the pinned Playwright setup in the adjacent render record.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const directory = 'docs/08-reference/diagrams';
  const names = ['tier1-flux-ownership', 'platform-cluster-runtime'];
  fs.mkdirSync('.tmp/tier1-flux-render', {recursive:true});
  const browser = await chromium.launch({headless: true, channel: 'msedge'});
  const results = [];
  for (const name of names) for (const width of [1100, 760]) for (const theme of ['light', 'dark']) {
    const svg = fs.readFileSync(path.join(directory, `${name}.svg`), 'utf8');
    const page = await browser.newPage({viewport: {width, height: 1000}});
    await page.setContent(`<style>body{margin:20px;background:${theme === 'light' ? '#fff' : '#0d1117'}}svg{max-width:100%;height:auto;display:block}</style>${svg}`);
    const checks = await page.evaluate(() => {
      const elements = [...document.querySelectorAll('g[id]')];
      const overflow = [];
      for (const group of elements) {
        const rectangle = [...group.children].find(n => n.tagName === 'rect');
        if (!rectangle) continue;
        const box = rectangle.getBBox();
        for (const text of [...group.children].filter(n => n.tagName === 'text')) {
          const b = text.getBBox();
          if (b.x < box.x || b.x + b.width > box.x + box.width || b.y < box.y || b.y + b.height > box.y + box.height)
            overflow.push({id: group.id, text: text.textContent, box: {x:b.x,y:b.y,width:b.width,height:b.height}});
        }
      }
      return {overflow, font: getComputedStyle(document.querySelector('svg')).font,
        palette: elements.map(g => ({id:g.id,fill:getComputedStyle(g).fill,color:getComputedStyle(g).color,stroke:getComputedStyle(g).stroke})),
        tiers: ['T2','T1','T0'].filter(id=>document.getElementById(id)).map(id => {const b=document.getElementById(id).getBoundingClientRect(); return {id,x:b.x,y:b.y,width:b.width,height:b.height};})};
    });
    await page.setContent(`<style>body{margin:20px;background:${theme === 'light' ? '#fff' : '#0d1117'}}img{max-width:100%;height:auto;display:block}</style><img alt="Tier 1 Flux ownership" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}">`);
    await page.evaluate(() => document.querySelector('img').decode());
    const output = name === 'tier1-flux-ownership' ? directory : '.tmp/tier1-flux-render';
    await page.locator('img').screenshot({path:path.join(output,`${name}-${width}-${theme}.png`)});
    results.push({name, width, theme, browser: browser.version(), ...checks});
    await page.close();
  }
  if (process.env.DIAGRAM_MERMAID) {
    for (const [name,document] of [['controllers','docs/01-architecture/10-delivery/02-controllers.md'],
      ['approval-controls','docs/01-architecture/10-delivery/approval-controls.md'],
      ['delivery-operations','docs/05-operations/05-delivery.md']]) {
    const markdown = fs.readFileSync(document, 'utf8');
    const code = [...markdown.matchAll(/```mermaid\r?\n([\s\S]*?)```/g)][0][1];
    for (const width of [1100, 760]) for (const theme of ['light', 'dark']) {
      const page = await browser.newPage({viewport:{width,height:1000}});
      await page.setContent(`<style>body{margin:20px;background:${theme === 'light' ? '#fff' : '#0d1117'}}svg{max-width:100%;height:auto;display:block}</style><main></main>`);
      await page.addScriptTag({path:process.env.DIAGRAM_MERMAID});
      await page.evaluate(async ({code,theme}) => {
        mermaid.initialize({startOnLoad:false,securityLevel:'loose',theme:theme === 'dark' ? 'dark' : 'default'});
        const {svg} = await mermaid.render('controllers',code);
        document.querySelector('main').innerHTML=svg;
      }, {code,theme});
      await page.locator('main').screenshot({path:`.tmp/tier1-flux-render/${name}-${width}-${theme}.png`});
      results.push({name,width,theme,browser:browser.version(),parsed:true});
      await page.close();
    }
    }
  }
  await browser.close();
  fs.mkdirSync('.tmp/tier1-flux-render', {recursive:true});
  fs.writeFileSync('.tmp/tier1-flux-render/report.json', JSON.stringify(results, null, 2));
  process.stdout.write(JSON.stringify({renders:results.length, browser:results[0].browser,
    svgOverflow:results.flatMap(r=>r.overflow || [])}));
  if (results.some(r=>(r.overflow || []).length)) process.exitCode=1;
})();
