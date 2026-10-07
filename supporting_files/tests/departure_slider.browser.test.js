const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8').replace('    init();', '');
    await page.setContent(html);
    await page.evaluate(() => {
      activeSearchState = { routes: [], queryTime: 1320, mode: 'leave', date: new Date(2026, 9, 6) };
      renderActiveSearchResults();
      els.results.addEventListener('input', handleDepartureRangeInput);
      window.originalSlider = document.querySelector('#departure-range-slider');
    });
    const slider = page.locator('#departure-range-slider');
    await slider.scrollIntoViewIfNeeded();
    const box = await slider.boundingBox();
    await page.mouse.move(box.x + box.width - 12, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height / 2, {steps:12});
    const midway = await slider.inputValue();
    await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2, {steps:12});
    await page.mouse.up();
    await page.evaluate(() => new Promise(requestAnimationFrame));
    assert(Number(await slider.inputValue()) < Number(midway), 'One continuous drag keeps moving across renders');
    assert(await page.evaluate(() => originalSlider === document.querySelector('#departure-range-slider')), 'Native slider is preserved');
    await slider.focus();
    const before = Number(await slider.inputValue());
    await page.keyboard.press('ArrowRight');
    await page.evaluate(() => new Promise(requestAnimationFrame));
    assert.equal(Number(await slider.inputValue()), before + 1);
    assert(await slider.evaluate(el => el === document.activeElement), 'Keyboard focus survives rendering');
    await page.keyboard.press('End');
    await page.evaluate(() => new Promise(requestAnimationFrame));
    assert.equal(await slider.inputValue(), '24');
    assert.equal(await slider.getAttribute('aria-valuetext'), 'Full search period');
    assert.match(await page.locator('#departure-range-copy').textContent(), /9:59 PM tomorrow/);
    console.log('Slider continuous drag, stable element, keyboard focus, range label and next-day boundary passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
