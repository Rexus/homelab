// Use the pinned Playwright setup and working directory in the adjacent render record.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  // Sources resolve beside this script in upstream and generated auto-docs.
  const directory = __dirname;
  const documents = path.resolve(directory, '../..');
  const review = path.resolve('.tmp/tier1-flux-render');
  const views = [
    ['tier1-flux-ownership', 'Tier 1 reconciliation and promotion ownership'],
    ['platform-cluster-runtime', 'Tier 1 Kubernetes node and delivery runtime placement'],
    ['kubernetes-platform', 'Tier 0 Kubernetes platform services'],
    ['infrastructure-runner-placement', 'Protected infrastructure execution and independent recovery'],
  ];
  fs.mkdirSync(review, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const results = [];
  try {
    for (const [name, title] of views) {
      const svg = fs.readFileSync(path.join(directory, `${name}.svg`), 'utf8');
      for (const width of [1100, 760]) {
        for (const theme of ['light', 'dark']) {
          const page = await browser.newPage({ viewport: { width, height: 1000 } });
          const background = theme === 'light' ? '#fff' : '#0d1117';
          await page.setContent(`<style>body{margin:20px;background:${background}}svg{max-width:100%;height:auto;display:block}</style>${svg}`);
          const checks = await page.evaluate(() => {
            const elements = [...document.querySelectorAll('g[id]')];
            const overflow = [];
            for (const group of elements) {
              const rectangle = [...group.children].find(node => node.tagName === 'rect');
              if (!rectangle) continue;
              const box = rectangle.getBBox();
              for (const text of [...group.children].filter(node => node.tagName === 'text')) {
                const bounds = text.getBBox();
                if (bounds.x < box.x || bounds.x + bounds.width > box.x + box.width ||
                    bounds.y < box.y || bounds.y + bounds.height > box.y + box.height) {
                  overflow.push({ id: group.id, text: text.textContent,
                    box: { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height } });
                }
              }
            }
            return {
              overflow,
              font: getComputedStyle(document.querySelector('svg')).font,
              palette: elements.map(group => ({
                id: group.id,
                fill: getComputedStyle(group).fill,
                color: getComputedStyle(group).color,
                stroke: getComputedStyle(group).stroke,
              })),
              tiers: ['T2', 'T1', 'T0'].filter(id => document.getElementById(id)).map(id => {
                const bounds = document.getElementById(id).getBoundingClientRect();
                return { id, x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
              }),
            };
          });
          await page.setContent(`<style>body{margin:20px;background:${background}}img{max-width:100%;height:auto;display:block}</style><img alt="${title}" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}">`);
          await page.evaluate(() => document.querySelector('img').decode());
          const output = name === 'tier1-flux-ownership' ? directory : review;
          await page.locator('img').screenshot({ path: path.join(output, `${name}-${width}-${theme}.png`) });
          results.push({ name, width, theme, browser: browser.version(), ...checks });
          await page.close();
        }
      }
    }
    if (process.env.DIAGRAM_MERMAID) {
      const inlineViews = [
        ['controllers', '01-architecture/10-delivery/02-controllers.md'],
        ['approval-controls', '01-architecture/10-delivery/approval-controls.md'],
        ['delivery-operations', '05-operations/05-delivery.md'],
      ];
      for (const [name, document] of inlineViews) {
        const markdown = fs.readFileSync(path.join(documents, document), 'utf8');
        const code = [...markdown.matchAll(/```mermaid\r?\n([\s\S]*?)```/g)][0][1];
        for (const width of [1100, 760]) {
          for (const theme of ['light', 'dark']) {
            const page = await browser.newPage({ viewport: { width, height: 1000 } });
            const background = theme === 'light' ? '#fff' : '#0d1117';
            await page.setContent(`<style>body{margin:20px;background:${background}}svg{max-width:100%;height:auto;display:block}</style><main></main>`);
            await page.addScriptTag({ path: process.env.DIAGRAM_MERMAID });
            await page.evaluate(async ({ code, theme }) => {
              mermaid.initialize({ startOnLoad: false, securityLevel: 'loose',
                theme: theme === 'dark' ? 'dark' : 'default' });
              const { svg } = await mermaid.render('controllers', code);
              document.querySelector('main').innerHTML = svg;
            }, { code, theme });
            await page.locator('main').screenshot({ path: path.join(review, `${name}-${width}-${theme}.png`) });
            results.push({ name, width, theme, browser: browser.version(), parsed: true });
            await page.close();
          }
        }
      }
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(review, 'report.json'), JSON.stringify(results, null, 2));
  process.stdout.write(JSON.stringify({ renders: results.length, browser: results[0].browser,
    svgOverflow: results.flatMap(result => result.overflow || []) }));
  if (results.some(result => (result.overflow || []).length)) process.exitCode = 1;
})();
