// Pinned tool setup and review scope: vmid-convention-render.md.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const source = path.resolve(__dirname, '../../02-conventions/vmid-convention.svg');
  const output = path.resolve('.tmp/vmid-convention-render');
  const svg = fs.readFileSync(source, 'utf8');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const report = [];
  try {
    for (const width of [1100, 760]) {
      for (const theme of ['light', 'dark']) {
        const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 1 });
        const background = theme === 'light' ? '#ffffff' : '#0d1117';
        const style = `<style>body{margin:20px;background:${background}}svg,img{display:block;max-width:100%;height:auto}</style>`;
        await page.setContent(style + svg);
        await page.evaluate(() => document.fonts.ready);
        const geometry = await page.locator('svg').evaluate(root => {
          const bounds = root.getBoundingClientRect();
          const labels = [...root.querySelectorAll('text')].map(text => ({
            text: text.textContent, bounds: text.getBoundingClientRect().toJSON()
          }));
          const clipped = labels.filter(({ bounds: label }) => label.left < bounds.left || label.right > bounds.right ||
            label.top < bounds.top || label.bottom > bounds.bottom);
          const collisions = [];
          for (let i = 0; i < labels.length; i++) {
            for (let j = i + 1; j < labels.length; j++) {
              const a = labels[i].bounds, b = labels[j].bounds;
              if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) {
                collisions.push([labels[i].text, labels[j].text]);
              }
            }
          }
          return { width: bounds.width, height: bounds.height, clipped, collisions };
        });
        if (geometry.clipped.length || geometry.collisions.length) {
          throw new Error(`VMID ${width}/${theme}: ${JSON.stringify(geometry)}`);
        }
        // Match Markdown's image embedding after inspecting the editable SVG text bounds.
        await page.setContent(style + `<img alt="Proxmox VMID convention" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}">`);
        await page.locator('img').evaluate(image => image.decode());
        await page.screenshot({ path: path.join(output, `vmid-${width}-${theme}.png`),
          clip: { x: 0, y: 0, width, height: Math.ceil(geometry.height + 40) } });
        report.push({ source, browser: browser.version(), viewport: width, theme, ...geometry });
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Rendered ${report.length} VMID cases without clipping or label collisions.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
