require('@testing-library/jest-dom');
const fs = require('fs');
const path = require('path');

beforeEach(() => {
  document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  document.querySelectorAll('script').forEach(s => {
    if (s.textContent) eval(s.textContent + '\nif(typeof toggleUnit==="function")window.toggleUnit=toggleUnit;');
  });
});

test('City name and temperature are visible on load', () => {
  const cityName = document.getElementById('cityName');
  const currentTemp = document.getElementById('currentTemp');
  expect(cityName).toBeInTheDocument();
  expect(cityName.textContent).toBe('New York');
  expect(currentTemp).toBeInTheDocument();
  expect(currentTemp.textContent).toBe('22');
});

test('Weather condition with emoji icon is displayed', () => {
  expect(document.getElementById('conditionLabel').textContent).toBe('Sunny');
  expect(document.getElementById('conditionIcon').textContent).toBe('☀️');
});

test('High and low temperatures are shown', () => {
  expect(document.getElementById('highTemp').textContent).toBe('26°');
  expect(document.getElementById('lowTemp').textContent).toBe('17°');
});

test('Toggle button switches between Celsius and Fahrenheit correctly', () => {
  jest.useFakeTimers();

  const toggleBtn = document.getElementById('toggleBtn');

  // Initial state is Celsius
  expect(document.getElementById('unitLabel').textContent).toBe('°C');
  expect(document.getElementById('currentTemp').textContent).toBe('22');
  expect(toggleBtn.textContent).toBe('Switch to °F');

  // Click once → Fahrenheit
  toggleBtn.click();
  jest.runAllTimers();

  expect(document.getElementById('unitLabel').textContent).toBe('°F');
  expect(document.getElementById('currentTemp').textContent).toBe('72');
  expect(document.getElementById('highTemp').textContent).toBe('79°');
  expect(document.getElementById('lowTemp').textContent).toBe('63°');
  expect(toggleBtn.textContent).toBe('Switch to °C');

  // Click again → back to Celsius
  toggleBtn.click();
  jest.runAllTimers();

  expect(document.getElementById('unitLabel').textContent).toBe('°C');
  expect(document.getElementById('currentTemp').textContent).toBe('22');
  expect(document.getElementById('highTemp').textContent).toBe('26°');
  expect(document.getElementById('lowTemp').textContent).toBe('17°');
  expect(toggleBtn.textContent).toBe('Switch to °F');

  jest.useRealTimers();
});
