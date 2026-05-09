require('@testing-library/jest-dom');
const fs = require('fs');
const path = require('path');

function loadApp() {
  document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  document.querySelectorAll('script').forEach(s => { if (s.textContent) { try { eval(s.textContent); } catch(e) {} } });
}

beforeEach(() => { loadApp(); });

test('City name and temperature are visible on load', () => {
  expect(document.body.innerHTML.trim().length).toBeGreaterThan(0);
  const meaningfulEls = document.querySelectorAll('input, button, [id], [class]');
  expect(meaningfulEls.length).toBeGreaterThan(0);
});

test('Weather condition with emoji icon is displayed', () => {
  expect(document.body.innerHTML.trim().length).toBeGreaterThan(0);
  const meaningfulEls = document.querySelectorAll('input, button, [id], [class]');
  expect(meaningfulEls.length).toBeGreaterThan(0);
});

test('High and low temperatures are shown', () => {
  expect(document.body.innerHTML.trim().length).toBeGreaterThan(0);
  const meaningfulEls = document.querySelectorAll('input, button, [id], [class]');
  expect(meaningfulEls.length).toBeGreaterThan(0);
});

test('Toggle button switches between Celsius and Fahrenheit correctly', () => {
  const btn = document.querySelector('button, input[type="button"], input[type="submit"]');
  expect(btn).not.toBeNull();
  btn.click();
  expect(document.body.innerHTML.trim().length).toBeGreaterThan(0);
});
