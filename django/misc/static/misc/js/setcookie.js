'use strict';

function main() {
  var setButton = document.querySelector('#set');
  setButton.addEventListener('click', setAction);
  var deleteButton = document.querySelector('#delete');
  deleteButton.addEventListener('click', deleteAction);
  addNameAutofills();
}

function setAction() {
  var name = document.querySelector('#cookieName').value;
  var value = document.querySelector('#cookieValue').value;
  if (name) {
    setCookie(name, value, '/');
  }
  var cookies = parseCookies(document.cookie);
  displayCookies(cookies);
}

function deleteAction() {
  var name = document.querySelector('#cookieName').value;
  if (name) {
    deleteCookie(name, '/');
  }
  var cookies = parseCookies(document.cookie);
  displayCookies(cookies);
}

function nameAutofill(event) {
  var newData = this.textContent;
  var dataType = this.className;
  if (dataType == 'name') {
    var formElement = document.querySelector('#cookieName');
  } else if (dataType == 'value') {
    var formElement = document.querySelector('#cookieValue');
  }
  formElement.value = newData;
};

function addNameAutofills() {
  var table = document.querySelector('#currentCookies tbody');
  for (var i = 0; i < table.children.length; i++) {
    var row = table.children[i];
    for (var j = 0; j < row.children.length; j++) {
      row.children[j].addEventListener('click', nameAutofill);
    }
  }
}

function displayCookies(cookies) {
  var table = document.querySelector('#currentCookies tbody');
  // First, delete all the existing rows.
  while (table.children.length > 0) {
    table.removeChild(table.children[0]);
  }
  // Then, add a row for each cookie.
  var names = Object.keys(cookies).sort();
  for (var i = 0; i < names.length; i++) {
    var cookie = cookies[names[i]];
    var rowElement = makeTableRow(cookie.name, cookie.value);
    table.appendChild(rowElement);
  }
  addNameAutofills();
}

function makeTableRow(name, value) {
  var nameElement = document.createElement('td');
  nameElement.className = 'name';
  var nameText = document.createTextNode(name);
  nameElement.appendChild(nameText);
  var valueElement = document.createElement('td');
  valueElement.className = 'value';
  var valueText = document.createTextNode(value);
  valueElement.appendChild(valueText);
  var rowElement = document.createElement('tr');
  rowElement.appendChild(nameElement);
  rowElement.appendChild(valueElement);
  return rowElement;
}

function parseCookies(cookiesStr) {
  var cookies = {};
  var cookieBits = cookiesStr.split('; ');
  for (var i = 0; i < cookieBits.length; i++) {
    var cookieBit = cookieBits[i];
    var name = '';
    var value = '';
    var fields = cookieBit.split('=');
    for (var j = 0; j < fields.length; j++) {
      if (j == 0) {
        name = fields[j];
      } else if (j === 1) {
        value = fields[j];
      } else {
        value += '='+fields[j];
      }
    }
    if (name === 'path' || name === 'domain' || name === 'max-age' || name === 'expires' ||
        name === 'secure') {
      if (typeof cookie !== 'undefined') {
        cookie[name] = value;
      }
    } else {
      if (typeof cookie !== 'undefined') {
        cookies[cookie.name] = cookie;
      }
      var cookie = {'name':name, 'value':value};
    }
  }
  if (typeof cookie !== 'undefined') {
    cookies[cookie.name] = cookie;
  }
  return cookies;
}

function setCookie(cookieName, cookieValue, path, expires) {
  var cookieStr = cookieName+'='+cookieValue;
  if (typeof expires === 'string') {
    cookieStr += '; expires='+expires;
  }
  if (typeof path === 'string') {
    cookieStr += '; path='+path;
  }
  console.log('Setting cookie to "'+cookieStr+'"');
  document.cookie = cookieStr;
}

function deleteCookie(cookieName, path) {
  setCookie(cookieName, '', path, 'Thu, 01 Jan 1970 00:00:01 UTC');
}

main();
