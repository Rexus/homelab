// Run from the upstream checkout with Playwright and Microsoft Edge available.
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');

(async () => {
  const folder = path.resolve('.tmp/intake-render');
  const base = 'architecture/generated/software-intake/';
  const impactView = 'architecture/views/software-intake/asset-impact.svg';
  const index = JSON.parse(fs.readFileSync(base + 'reverse-trace.json', 'utf8')).assets;
  const tf = 'tier-2/terraform/deployments/cache/main.tf';
  const apt = 'tests/test_tier_package_policy.py';
  const squid = 'tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2';
  const report = { journey: [], views: [], assets: Object.keys(index).length };
  const url = (file, id) => pathToFileURL(path.resolve(file)).href + (id ? '#' + id : '');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  report.browser = browser.version();
  try {
    const p = await browser.newPage({ viewport: { width: 1100, height: 1200 } });
    // The architecture README links directly to the focused change-impact view.
    await p.goto(url(impactView));
    for (const [selector, suffix] of [
      ['[data-view="index"] a[aria-label="Terraform"]', 'asset-impact.svg#Terraform'],
      [`[data-view="Terraform"] a:has([data-asset="${tf}"])`, 'asset-impact.svg#' + index[tf].id],
      [`[data-view="${index[tf].id}"] a:has([data-element="F-http"])`, 'function-views.svg#F-http'],
      ['[data-view="F-http"] a[href="policy-proxy/contract.svg"]', 'policy-proxy/contract.svg'],
    ]) {
      await p.locator(selector).click();
      await p.waitForURL(u => u.href.endsWith(suffix));
      report.journey.push(suffix);
    }
    await p.goBack();
    if (!p.url().endsWith('function-views.svg#F-http')) throw new Error('Back lost the function context');
    await p.goto(url(impactView, index[squid].id));
    await p.locator(`[data-view="${index[squid].id}"] a[aria-label="F-http"]`).click();
    await p.waitForURL(u => u.href.endsWith('function-views.svg#F-http'));
    report.journey.push('Squid source → HTTP forwarding function');
    await p.goto(url(impactView, index[apt].id));
    const clientPane = p.locator(`[data-view="${index[apt].id}"]`);
    if (await clientPane.locator('[data-element="F-http"],[data-element="SC-http-denied"]').count()) throw new Error('Client evidence gained unrelated behavior');
    await clientPane.locator('a:has([data-element="F-verify"])').click();
    await p.waitForURL(u => u.href.endsWith('function-views.svg#F-verify'));
    report.journey.push('function-views.svg#F-verify');

    await p.goto(url(impactView));
    const ids = await p.locator('svg > view').evaluateAll(nodes => nodes.map(n => n.id));
    for (const id of ids) {
      await p.goto(url(impactView, id));
      const result = await p.evaluate(id => {
        const active = document.querySelector(`svg[data-view="${id}"]`);
        if (!active || getComputedStyle(active).visibility !== 'visible') throw new Error('View is hidden');
        const overflow = [];
        for (const group of active.querySelectorAll('.explorer-card')) {
          const box = group.querySelector('rect').getBoundingClientRect();
          for (const text of group.querySelectorAll('text')) {
            const b = text.getBoundingClientRect();
            if (b.left < box.left-1 || b.right > box.right+1 || b.top < box.top-1 || b.bottom > box.bottom+1) overflow.push(text.textContent);
          }
        }
        const clone = active.cloneNode(true);
        for (const attr of ['x','y','width','height','data-view']) clone.removeAttribute(attr);
        return { overflow, svg: clone.outerHTML };
      }, id);
      if (result.overflow.length) throw new Error(id + ': ' + result.overflow.join(', '));
      report.views.push(id);
      if (['index', index[tf].id, index[apt].id].includes(id)) {
        const label = id === 'index' ? 'index' : id === index[tf].id ? 'terraform' : 'client-test';
        for (const width of [1100, 760]) for (const theme of ['light', 'dark']) {
          const preview = await browser.newPage({ viewport: { width, height: 1200 } });
          await preview.setContent(`<style>body{margin:20px;background:${theme === 'light' ? '#fff' : '#0d1117'}}svg{display:block;width:100%;height:auto}main{background:white}</style><main>${result.svg}</main>`);
          await preview.locator('main').screenshot({ path: path.join(folder, `reverse-${label}-${width}-${theme}.png`) });
          await preview.close();
        }
      }
    }
    await p.close();
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(folder, 'reverse-browser-report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Passed ${report.journey.length} browser steps, ${report.views.length} reverse views and 12 previews for ${report.assets} traced assets.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
