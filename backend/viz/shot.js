const { chromium } = require('/opt/homebrew/lib/node_modules/playwright/index.js');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1220, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + process.cwd() + '/viz/out/kalkulation_baum.html');
  await p.waitForTimeout(300);
  // full first case
  const cases = await p.$$('.case');
  await cases[0].screenshot({ path: 'viz/out/shot_case1.png' });
  await b.close();
  console.log('done');
})();
