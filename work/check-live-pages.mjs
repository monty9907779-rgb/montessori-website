import { chromium } from 'playwright';

const urls = [
  'https://montessori-ksa.com/',
  'https://montessori-ksa.com/login/',
  'https://montessori-ksa.com/dashboard/',
  'https://montessori-ksa.com/accounts/',
];

const browser = await chromium.launch({headless: true});
for (const url of urls) {
  const page = await browser.newPage({viewport: {width: 1365, height: 900}, locale: 'ar-SA'});
  const errors = [];
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) errors.push(`${msg.type()}: ${msg.text()}`);
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  let status = 0;
  try {
    const response = await page.goto(url, {waitUntil: 'networkidle', timeout: 30000});
    status = response?.status() ?? 0;
  } catch (error) {
    errors.push(`navigation: ${error.message}`);
  }
  const title = await page.title().catch(() => '');
  const text = await page.locator('body').innerText({timeout: 5000}).catch((error) => `ERR ${error.message}`);
  const name = new URL(url).pathname.replace(/\W+/g, '-') || 'root';
  const screenshot = `/Users/mohamedmontaser/Documents/Codex/2026-09-11/files-pasted-by-the-user-user/work/live-${name}.png`;
  await page.screenshot({path: screenshot, fullPage: false}).catch(() => {});
  console.log(JSON.stringify({url, status, finalUrl: page.url(), title, text: text.slice(0, 700), errors: errors.slice(0, 12), screenshot}, null, 2));
  await page.close();
}
await browser.close();
