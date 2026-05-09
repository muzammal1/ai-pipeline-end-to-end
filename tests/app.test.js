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

  input.value = 'Buy groceries';
  input.dispatchEvent(new Event('input'));
  addBtn.click();

  const list = document.getElementById('todo-list');
  const texts = Array.from(list.querySelectorAll('.todo-text')).map(el => el.textContent);
  expect(texts).toContain('Buy groceries');
});

test('Mark a todo as complete with strikethrough styling', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');

  input.value = 'Write tests';
  addBtn.click();

  const list = document.getElementById('todo-list');
  const checkbox = list.querySelector('input[type="checkbox"]');
  checkbox.click();

  const todoItem = list.querySelector('.todo-item');
  expect(todoItem).toHaveClass('done');
  const todoText = todoItem.querySelector('.todo-text');
  expect(todoText).toHaveStyle('text-decoration: line-through');
});

test('Delete a todo item', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');

  input.value = 'Task to delete';
  addBtn.click();

  const list = document.getElementById('todo-list');
  expect(list.querySelector('.todo-item')).not.toBeNull();

  list.querySelector('.delete-btn').click();

  expect(list.querySelector('.todo-item')).toBeNull();
});

test('Show count of remaining incomplete items', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');

  input.value = 'Task 1';
  addBtn.click();
  input.value = 'Task 2';
  addBtn.click();
  input.value = 'Task 3';
  addBtn.click();

  const list = document.getElementById('todo-list');
  const checkboxes = list.querySelectorAll('input[type="checkbox"]');
  checkboxes[0].click();

  const countEl = document.getElementById('count');
  expect(countEl.textContent).toBe('2 items remaining');
});
