// Export the existing foundation figure; its guide remains the sole design source.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {chromium} = require(process.env.DIAGRAM_PLAYWRIGHT || 'playwright');
const sourcePath = 'docs/03-deployment/foundation/bootstrap/README.md';
const target = 'architecture/views/platform/hosting/bootstrap-reference.svg';
const source = fs.readFileSync(sourcePath,'utf8').match(/```mermaid\s*([\s\S]*?)```/)[1].trim().replace(/\r\n/g,'\n');
const hash = crypto.createHash('sha256').update(source).digest('hex');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    await page.setContent('<html><body></body></html>');
    await page.addScriptTag({path:process.env.DIAGRAM_MERMAID || require.resolve('mermaid/dist/mermaid.min.js')});
    const result = await page.evaluate(async ({source,sourcePath,hash}) => {
      mermaid.initialize({startOnLoad:false,securityLevel:'strict',deterministicIds:true,
        deterministicIDSeed:'bootstrap-foundation-reference',flowchart:{htmlLabels:false}});
      const {svg: rendered} = await mermaid.render('bootstrap-foundation-reference',source);
      document.body.innerHTML = rendered;
      const figure = document.querySelector('svg');
      const host = figure.querySelector('g.cluster[id="bootstrap-foundation-reference-VM"]');
      if (!host) throw Error('Foundation figure no longer identifies the boot-1 VM boundary');
      host.setAttribute('data-model','BOOT-host');
      const [, , width, height] = figure.getAttribute('viewBox').split(/\s+/).map(Number);
      const figureHeight = height * 960 / width;
      const NS = 'http://www.w3.org/2000/svg';
      const el = (name, attrs={}, text) => {
        const e=document.createElementNS(NS,name);
        for(const [k,v] of Object.entries(attrs)) e.setAttribute(k,String(v));
        if(text) e.textContent=text;
        return e;
      };
      const outer=el('svg',{xmlns:NS,viewBox:`0 0 960 ${figureHeight+132}`,role:'img',
        'data-subject':'BOOT-host','data-reference-source':sourcePath,'data-source-sha256':hash});
      outer.append(el('title',{},'Bootstrap execution host — foundation reference'));
      outer.append(el('desc',{},'Existing guide-owned manual VM option. Only the boot-1 boundary is linked to the native model; internal design remains a mapped reference.'));
      outer.append(el('rect',{width:960,height:figureHeight+132,fill:'white'}));
      const text=(parent,value,x,y,size=15)=>parent.append(el('text',{x,y,
        style:`font:${size}px Arial,sans-serif;fill:#1f2937;text-anchor:middle`},value));
      text(outer,'Bootstrap execution host',480,29,23);
      text(outer,'Foundation reference · Manual VM option · Internal details remain guide-owned',480,54);
      figure.setAttribute('x','0'); figure.setAttribute('y','68');
      figure.setAttribute('width','960'); figure.setAttribute('height',String(figureHeight));
      figure.removeAttribute('style');
      outer.append(figure);
      const y=figureHeight+76;
      outer.append(el('rect',{x:0,y,width:960,height:56,fill:'#eef2f6'}));
      for(const [i,[name,href]] of [
        ['Clone use case','clone-repository.svg'],
        ['Intake design','../../software-intake/logical.svg'],
        ['Documentation','../../../../docs/03-deployment/foundation/bootstrap/README.md#figure-1-bootstrap-execution-host'],
      ].entries()) {
        const a=el('a',{href,target:'_top','aria-label':name});
        a.append(el('rect',{x:i*320,y,width:320,height:56,fill:'transparent'}));
        text(a,name,i*320+160,y+34); outer.append(a);
      }
      return new XMLSerializer().serializeToString(outer)+String.fromCharCode(10);
    },{source,sourcePath,hash});
    fs.mkdirSync(path.dirname(target),{recursive:true}); fs.writeFileSync(target,result);
    console.log('Rendered existing foundation reference: '+target);
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
