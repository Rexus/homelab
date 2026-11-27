// Review generated structure, behavior and navigation views from the upstream checkout.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const output = path.resolve('.tmp/intake-render');
  fs.mkdirSync(output, { recursive: true });
  const views = ['logical', 'solution'].map(name => ({
    name, svg: fs.readFileSync('architecture/generated/software-intake/' + name + '.svg', 'utf8'),
  }));
  views.push({ name: 'system-overall', svg: fs.readFileSync('architecture/generated/HomelabSystemOverview.svg', 'utf8') });
  views.push({ name: 'platform-overview', svg: fs.readFileSync('architecture/generated/platform/SharedPlatformOverview.svg', 'utf8') });
  views.push({ name: 'use-cases', svg: fs.readFileSync('architecture/generated/software-intake/SoftwareIntakeUseCases.svg', 'utf8') });
  views.push({ name: 'resource-dependencies', svg: fs.readFileSync('architecture/generated/software-intake/solution/SoftwareIntakeResources.svg', 'utf8') });
  for (const name of ['http', 'https']) {
    views.push({ name, mermaid: fs.readFileSync(`artifacts/architecture/generated/software-intake/${name}.mmd`, 'utf8') });
  }
  const map = fs.readFileSync('docs/01-architecture/model-map.md', 'utf8');
  views.push({ name: 'model-map', mermaid: map.match(/```mermaid\s*([\s\S]*?)```/)[1] });
  const contexts = JSON.parse(fs.readFileSync('scripts/architecture/config/views/design-context.json', 'utf8')).scopes;
  for (const scope of contexts.filter(s => s.svg && !['system', 'platform'].includes(s.key))) {
    views.push({ name: 'context-' + scope.key, svg: fs.readFileSync(scope.svg, 'utf8') });
  }
  const overviewOnly = process.argv.includes('--overviews');
  const sequencesOnly = process.argv.includes('--sequences');
  const selectedViews = sequencesOnly ? views.filter(v => ['http','https'].includes(v.name)) : overviewOnly ? views.filter(v => v.name === 'system-overall' || v.name === 'platform-overview' || v.name.startsWith('context-')) : views;
  const report = [];
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const view of selectedViews) {
      for (const width of [1100, 760]) {
        for (const theme of ['light', 'dark']) {
          const page = await browser.newPage({ viewport: { width, height: 1200 } });
          const background = theme === 'light' ? '#ffffff' : '#0d1117';
          await page.setContent(`<style>body{margin:20px;background:${background}}svg{display:block;max-width:100%;height:auto}main{background:${view.svg || view.name === 'model-map' ? 'white' : background}}</style><main></main>`);
          if (view.mermaid) {
            await page.addScriptTag({ path: process.env.DIAGRAM_MERMAID || require.resolve('mermaid/dist/mermaid.min.js') });
            const svg = await page.evaluate(async ({ source, theme }) => {
              mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: theme === 'dark' ? 'dark' : 'neutral' });
              return (await mermaid.render('model-view', source)).svg;
            }, { source: view.mermaid, theme });
            await page.locator('main').evaluate((e, source) => { e.innerHTML = source; }, svg);
            if (width === 1100 && theme === 'light') fs.writeFileSync(path.join(output, view.name + '.svg'), svg);
          } else {
            await page.locator('main').evaluate((e, source) => { e.innerHTML = source; }, view.svg);
          }
          const overflow = await page.locator('main > svg').evaluate(root => {
            const bad = [];
            const frame = root.getBoundingClientRect();
            for (const text of root.querySelectorAll('text')) {
              const b = text.getBoundingClientRect();
              if (b.left < frame.left - 1 || b.right > frame.right + 1 || b.bottom > frame.bottom + 1 || b.top < frame.top - 1) bad.push(text.textContent);
            }
            for (const group of root.querySelectorAll('g[data-model],g[data-models],g[data-context]')) {
              const rect = [...group.children].find(e => e.tagName === 'rect');
              if (!rect) continue;
              const box = rect.getBoundingClientRect();
              for (const text of [...group.children].filter(e => e.tagName === 'text')) {
                const b = text.getBoundingClientRect();
                if (b.left < box.left || b.right > box.right || b.top < box.top || b.bottom > box.bottom) bad.push(group.id);
              }
            }
            for (const group of root.querySelectorAll('.context-card')) {
              const box = group.querySelector('rect').getBoundingClientRect();
              for (const text of group.querySelectorAll('text')) {
                const b = text.getBoundingClientRect();
                if (b.left < box.left || b.right > box.right || b.top < box.top || b.bottom > box.bottom) bad.push(text.textContent);
              }
            }
            return bad;
          });
          if (overflow.length) throw new Error(`Label overflow: ${view.name}: ${overflow.join(', ')}`);
          await page.locator('main').screenshot({ path: path.join(output, `${view.name}-${width}-${theme}.png`) });
          report.push({ name: view.name, width, theme, browser: browser.version(), overflow });
          await page.close();
        }
      }
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(output, sequencesOnly ? 'report-sequences.json' : overviewOnly ? 'report-overviews.json' : 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Rendered ${report.length} views to ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
