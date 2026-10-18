const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ timezoneId: 'Asia/Seoul' });
    const dates = [];
    for (const route of ['/faq.html']) {
      for (const [lang, question, pattern] of [
        ['en', 'How often is the schedule data updated?', /^[A-Z][a-z]+ \d{1,2}, \d{4}$/],
        ['es', '¿Con qué frecuencia se actualizan los horarios?', /^\d{1,2} de [a-z]+ de \d{4}$/],
        ['ko', '열차 시간표 데이터는 얼마나 자주 업데이트되나요?', /^\d{4}년 \d{1,2}월 \d{1,2}일$/],
      ]) {
        await page.goto(`${base}${route}?lang=${lang}`);
        const date = page.locator('[data-schedule-refresh-date]');
        await date.waitFor({ state: 'attached' });
        assert.equal(await page.locator('html').getAttribute('lang'), lang);
        const text = await date.textContent();
        assert.match(text, pattern);
        dates.push(text);
        const details = page.locator('details').filter({ has: date });
        const summary = details.locator('summary');
        assert.ok((await summary.textContent()).includes(question));
        await summary.click();
        const before = await details.evaluate(el => el.open);
        await summary.click();
        assert.equal(await details.evaluate(el => el.open), !before);
        const nextLanguage = lang === 'en' ? 'es' : 'en';
        await page.selectOption('#language-select', nextLanguage);
        assert.equal(new URL(page.url()).searchParams.get('lang') || 'en', nextLanguage);
        assert.equal(await page.locator('html').getAttribute('lang'), nextLanguage);
      }
    }
    console.log('FAQ: translated copy, date formats, disclosure toggles and language switching passed in Asia/Seoul timezone.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
