// Reproduce with the pinned tools in trust-render.md.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const output = path.resolve('.tmp/trust-render');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const report = [];
  try {
    for (const [name, file] of [
      ['trust', 'stage2-trust.svg'],
      ['ceremony', 'ceremony-environment.svg'],
      ['ceremony-live-cycle', 'ceremony-live-cycle.svg'],
      ['orca-key-custody', 'orca-key-custody.svg'],
    ]) {
      const svg = fs.readFileSync(path.join(__dirname, file), 'utf8');
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
              const shape = [...group.children].find(child => ['rect', 'path', 'polygon'].includes(child.tagName));
              if (!shape) continue;
              const box = shape.getBBox();
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
          await page.locator('main').screenshot({ path: path.join(output, `${name}-${width}-${theme}.png`) });
          report.push({ name, viewport_width: width, theme, browser: browser.version(), ...geometry });
          await page.close();
        }
      }
    }
    if (process.env.DIAGRAM_MERMAID) {
      for (const [name, file, anchor] of [
        ['hierarchy', '../../01-architecture/08-cryptography/01-certificate-authority.md'],
        ['maintenance', '../../01-architecture/08-cryptography/04-usb-hsm.md'],
        ['root-signing', '../../01-architecture/08-cryptography/01-certificate-authority.md', 'figure-root-signing-exchange'],
      ]) {
        const document = fs.readFileSync(path.resolve(__dirname, file), 'utf8');
        const start = anchor ? document.indexOf(`<a id="${anchor}"></a>`) : 0;
        if (start < 0) throw new Error(`Missing required anchor #${anchor} for ${name} in ${file}`);
        const block = document.slice(start).match(/```mermaid\n([\s\S]*?)```/);
        if (!block) throw new Error(`Missing Mermaid source for ${name} in ${file}`);
        const source = block[1];
        for (const width of [1100, 760]) {
          for (const theme of ['light', 'dark']) {
            const page = await browser.newPage({ viewport: { width, height: 1000 } });
            const background = theme === 'light' ? '#ffffff' : '#0d1117';
            await page.setContent(`<style>body{margin:20px;background:${background}}svg{display:block;max-width:100%;height:auto}</style><main></main>`);
            await page.addScriptTag({ path: process.env.DIAGRAM_MERMAID });
            await page.evaluate(async content => {
              mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
              document.querySelector('main').innerHTML = (await mermaid.render('trustDiagram', content)).svg;
            }, source);
            await page.locator('main').screenshot({ path: path.join(output, `${name}-${width}-${theme}.png`) });
            report.push({ name, viewport_width: width, theme, browser: browser.version() });
            await page.close();
          }
        }
      }
    }
  } finally {
    // Preserve completed-case evidence if a later native source fails to parse.
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    await browser.close();
  }
  console.log(`Rendered ${report.length} cases to ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
