require('@testing-library/jest-dom');
const fs = require('fs');
const path = require('path');

beforeEach(() => {
  document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  document.querySelectorAll('script').forEach(s => { if (s.textContent) eval(s.textContent); });
});

test('Add a new todo item via a text input and a button', () => {
  const input = document.getElementById('todo-input');
  const btn = document.getElementById('add-btn');

  input.value = 'Buy groceries';
  input.dispatchEvent(new Event('input'));
  btn.click();

  const items = document.querySelectorAll('.todo-item');
  expect(items).toHaveLength(1);
  expect(items[0].querySelector('.todo-text').textContent).toBe('Buy groceries');
});

test('Mark a todo as complete with strikethrough styling', () => {
  const input = document.getElementById('todo-input');
  const form = document.getElementById('add-form');

  input.value = 'Read a book';
  form.dispatchEvent(new Event('submit'));

  document.querySelector('.complete-btn').click();

  const todoItem = document.querySelector('.todo-item');
  expect(todoItem).toHaveClass('done');
  expect(todoItem.querySelector('.todo-text')).toHaveStyle('text-decoration: line-through');
});

test('Delete a todo item', () => {
  const input = document.getElementById('todo-input');
  const form = document.getElementById('add-form');

  input.value = 'Write tests';
  form.dispatchEvent(new Event('submit'));

  expect(document.querySelectorAll('.todo-item')).toHaveLength(1);

  document.querySelector('.delete-btn').click();

  expect(document.querySelectorAll('.todo-item')).toHaveLength(0);
});

test('Show a count of remaining incomplete items', () => {
  const input = document.getElementById('todo-input');
  const form = document.getElementById('add-form');

  input.value = 'Task one';
  form.dispatchEvent(new Event('submit'));
  input.value = 'Task two';
  form.dispatchEvent(new Event('submit'));

  const countEl = document.getElementById('remaining-count');
  expect(countEl.textContent).toBe('2 items remaining');

  document.querySelector('.complete-btn').click();

  expect(countEl.textContent).toBe('1 item remaining');
});
