const fs = require('fs');
const path = require('path');
const { fireEvent } = require('@testing-library/dom');
require('@testing-library/jest-dom');

function loadApp() {
  document.body.innerHTML = fs.readFileSync(
    path.resolve(__dirname, '../index.html'),
    'utf8'
  );
  // jsdom does not execute scripts set via innerHTML; run the inline script manually.
  // new Function avoids let/const re-declaration errors across beforeEach resets.
  const script = document.querySelector('script');
  // eslint-disable-next-line no-new-func
  new Function(script.textContent)();
}

function click(selector) {
  fireEvent.click(document.querySelector(selector));
}

function display() {
  return document.getElementById('current');
}

beforeEach(() => {
  loadApp();
});

test('Display updates when digit buttons are clicked', () => {
  click('[data-digit="5"]');
  expect(display()).toHaveTextContent('5');

  click('[data-digit="3"]');
  expect(display()).toHaveTextContent('53');
});

test('Evaluate expression when equals button is pressed and show result', () => {
  click('[data-digit="2"]');
  click('[data-op="+"]');
  click('[data-digit="3"]');
  click('[data-action="equals"]');
  expect(display()).toHaveTextContent('5');
});

test('Clear button resets the display to zero', () => {
  click('[data-digit="7"]');
  click('[data-digit="8"]');
  expect(display()).toHaveTextContent('78');

  click('[data-action="clear"]');
  expect(display()).toHaveTextContent('0');
});

test('Basic operations work: addition, subtraction, multiplication, division', () => {
  // Addition: 6 + 3 = 9
  click('[data-digit="6"]');
  click('[data-op="+"]');
  click('[data-digit="3"]');
  click('[data-action="equals"]');
  expect(display()).toHaveTextContent('9');

  // Subtraction: 9 - 4 = 5
  click('[data-action="clear"]');
  click('[data-digit="9"]');
  click('[data-op="-"]');
  click('[data-digit="4"]');
  click('[data-action="equals"]');
  expect(display()).toHaveTextContent('5');

  // Multiplication: 4 × 3 = 12
  click('[data-action="clear"]');
  click('[data-digit="4"]');
  click('[data-op="*"]');
  click('[data-digit="3"]');
  click('[data-action="equals"]');
  expect(display()).toHaveTextContent('12');

  // Division: 8 ÷ 2 = 4
  click('[data-action="clear"]');
  click('[data-digit="8"]');
  click('[data-op="/"]');
  click('[data-digit="2"]');
  click('[data-action="equals"]');
  expect(display()).toHaveTextContent('4');
});
