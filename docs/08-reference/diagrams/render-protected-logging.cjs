// Reproduce with the pinned tools in protected-logging-render.md.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  if (!process.env.DIAGRAM_MERMAID) throw new Error('Set DIAGRAM_MERMAID to the approved Mermaid bundle.');
  const docs = path.resolve(__dirname, '../..');
  const output = path.resolve('.tmp/logging-dns-render');
  fs.mkdirSync(output, { recursive: true });
  const figures = ['protected-logging', 'logging-receivers', 'logging-sender-routing', 'logging-shared-endpoint']
    .map(name => ({ name, svg: fs.readFileSync(path.join(__dirname, `${name}.svg`), 'utf8') }));
  for (const file of ['README.md']) {
    const text = fs.readFileSync(path.join(docs, '03-deployment/stage-02-logging', file), 'utf8');
    let index = 0;
    for (const match of text.matchAll(/```mermaid\r?\n([\s\S]*?)```/g)) {
      figures.push({ name: `${file.replace('.md', '')}-${++index}`, code: match[1] });
    }
  }
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const report = [];
  try {
    for (const figure of figures) {
      for (const width of [1100, 760]) {
        for (const theme of ['light', 'dark']) {
          const page = await browser.newPage({ viewport: { width, height: 1000 } });
          const background = theme === 'light' ? '#ffffff' : '#0d1117';
          await page.setContent(`<style>body{margin:20px;background:${background}}main{width:100%}svg{max-width:100%;height:auto;display:block}</style><main></main>`);
          if (figure.code) {
            await page.addScriptTag({ path: process.env.DIAGRAM_MERMAID });
            await page.evaluate(async ({ code, theme }) => {
              mermaid.initialize({ startOnLoad: false, theme: theme === 'dark' ? 'dark' : 'default' });
              await mermaid.parse(code);
              document.querySelector('main').innerHTML = (await mermaid.render('loggingDiagram', code)).svg;
            }, { code: figure.code, theme });
          } else {
            await page.locator('main').evaluate((element, svg) => { element.innerHTML = svg; }, figure.svg);
          }
          const geometry = await page.locator('svg').evaluate(svg => {
            const bounds = svg.getBoundingClientRect();
            const overflow = [];
            for (const group of svg.querySelectorAll('g[id]')) {
              const rect = [...group.children].find(child => child.tagName === 'rect');
              if (!rect) continue;
              const box = rect.getBBox();
              for (const text of [...group.children].filter(child => child.tagName === 'text')) {
                const label = text.getBBox();
                if (label.x < box.x || label.x + label.width > box.x + box.width ||
                    label.y < box.y || label.y + label.height > box.y + box.height) overflow.push(group.id);
              }
            }
            return { width: bounds.width, height: bounds.height, viewBox: svg.getAttribute('viewBox'), overflow };
          });
          if (geometry.width < 100 || geometry.height < 40 || geometry.width > width - 39 || geometry.overflow.length) {
            throw new Error(`${figure.name}: unexpected geometry ${JSON.stringify(geometry)}`);
          }
          await page.locator('main').screenshot({ path: path.join(output, `${figure.name}-${width}-${theme}.png`) });
          report.push({ name: figure.name, viewport_width: width, theme, browser: browser.version(), ...geometry });
          await page.close();
        }
      }
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Rendered ${report.length} logging cases to ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
