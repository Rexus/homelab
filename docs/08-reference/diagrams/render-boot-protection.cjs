// Reproduce with the pinned tools in boot-protection-render.md.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const source = path.join(__dirname, 'boot-integrity-key-protection.svg');
  const svg = fs.readFileSync(source, 'utf8');
  const output = path.resolve('.tmp/boot-protection-render');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const report = [];
  try {
    for (const width of [1100, 760]) {
      for (const theme of ['light', 'dark']) {
        const page = await browser.newPage({ viewport: { width, height: 1000 } });
        const background = theme === 'light' ? '#ffffff' : '#0d1117';
        await page.setContent(`<style>body{margin:20px;background:${background}}svg{display:block;max-width:100%;height:auto}</style><main></main>`);
        await page.locator('main').evaluate((element, content) => { element.innerHTML = content; }, svg);
        const geometry = await page.locator('svg').evaluate(root => {
          const bounds = root.getBoundingClientRect();
          const overflow = [];
          for (const group of root.querySelectorAll('g[id]')) {
            const rectangle = [...group.children].find(child => child.tagName === 'rect');
            if (!rectangle) continue;
            const box = rectangle.getBBox();
            for (const text of [...group.children].filter(child => child.tagName === 'text')) {
              const label = text.getBBox();
              if (label.x < box.x || label.x + label.width > box.x + box.width ||
                  label.y < box.y || label.y + label.height > box.y + box.height) overflow.push(group.id);
            }
          }
          return { width: bounds.width, height: bounds.height, viewBox: root.getAttribute('viewBox'), overflow };
        });
        if (geometry.width > width - 39 || geometry.overflow.length) {
          throw new Error(`Unexpected label geometry: ${JSON.stringify(geometry)}`);
        }
        await page.locator('main').screenshot({ path: path.join(output, `boot-protection-${width}-${theme}.png`) });
        report.push({ viewport_width: width, theme, browser: browser.version(), ...geometry });
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Rendered ${report.length} cases to ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
