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
  addBtn.click();

  const items = document.querySelectorAll('.todo-text');
  expect(items.length).toBe(1);
  expect(items[0].textContent).toBe('Buy groceries');
});

test('Mark a todo as complete with strikethrough styling', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');

  input.value = 'Test todo';
  addBtn.click();

  const checkbox = document.querySelector('.todo-item input[type="checkbox"]');
  checkbox.click();

  const todoItem = document.querySelector('.todo-item');
  expect(todoItem).toHaveClass('done');
});

test('Delete a todo item', () => {
  const input = document.getElementById('todo-input');
  const addBtn = document.getElementById('add-btn');

  input.value = 'Task to delete';
  addBtn.click();

  expect(document.querySelectorAll('.todo-item').length).toBe(1);

  const deleteBtn = document.querySelector('.delete-btn');
  deleteBtn.click();

  expect(document.querySelectorAll('.todo-item').length).toBe(0);
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

  expect(document.getElementById('remaining').textContent).toBe('3');

  const firstCheckbox = document.querySelector('.todo-item input[type="checkbox"]');
  firstCheckbox.click();

  expect(document.getElementById('remaining').textContent).toBe('2');
});
