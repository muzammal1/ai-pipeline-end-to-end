require('@testing-library/jest-dom');
const fs = require('fs');
const path = require('path');

beforeEach(() => {
  document.body.innerHTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  document.querySelectorAll('script').forEach(s => { if (s.textContent) eval(s.textContent); });
});

test('Add a todo item via a text input and a button', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');
  const list = document.getElementById('todo-list');

  input.value = 'Buy groceries';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  const items = list.querySelectorAll('li:not(.empty)');
  expect(items.length).toBe(1);
  expect(items[0].querySelector('.todo-text').textContent).toBe('Buy groceries');
});

test('Mark a todo as complete with strikethrough styling', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');
  const list = document.getElementById('todo-list');

  input.value = 'Walk the dog';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  const checkbox = list.querySelector('.todo-checkbox');
  checkbox.checked = true;
  checkbox.dispatchEvent(new Event('change'));

  const li = list.querySelector('li');
  expect(li).toHaveClass('done');
  expect(li.querySelector('.todo-text')).toHaveStyle('text-decoration: line-through');
});

test('Delete a todo item', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');
  const list = document.getElementById('todo-list');

  input.value = 'Read a book';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  expect(list.querySelectorAll('li:not(.empty)').length).toBe(1);

  const deleteBtn = list.querySelector('.delete-btn');
  deleteBtn.click();

  expect(list.querySelectorAll('li:not(.empty)').length).toBe(0);
});

test('Show count of remaining incomplete items', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');
  const list = document.getElementById('todo-list');
  const remaining = document.getElementById('remaining');

  input.value = 'Task one';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  input.value = 'Task two';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  expect(remaining.textContent).toBe('2');

  const checkbox = list.querySelector('.todo-checkbox');
  checkbox.checked = true;
  checkbox.dispatchEvent(new Event('change'));

  expect(remaining.textContent).toBe('1');
});
