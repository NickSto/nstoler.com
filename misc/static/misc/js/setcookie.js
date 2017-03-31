'use strict';

function main() {
  var setButton = document.querySelector('#set');
  setButton.addEventListener('click', setAction);
  var deleteButton = document.querySelector('#delete');
  deleteButton.addEventListener('click', deleteAction);
  displayCookies(parseCookies(document.cookie));
  addNameAutofills();
}

function setAction() {
  var name = document.querySelector('#cookieName').value;
  var value = document.querySelector('#cookieValue').value;
  if (name) {
    setCookie(name, value, '/', undefined, 20);
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
  var name = this.children[0].textContent;
  var value = this.children[1].textContent;
  var nameInput = document.querySelector('#cookieName');
  nameInput.value = name;
  var valueInput = document.querySelector('#cookieValue');
  valueInput.value = value;
};

function addNameAutofills() {
  var table = document.querySelector('#currentCookies tbody');
  for (var i = 0; i < table.children.length; i++) {
    var row = table.children[i];
    row.addEventListener('click', nameAutofill);
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

function setCookie(cookieName, cookieValue, path, domain, expires) {
  var cookieStr = cookieName+'='+cookieValue;
  if (typeof path === 'string') {
    cookieStr += '; path='+path;
  } else {
    cookieStr += '; path=/';
  }
  if (typeof domain === 'string') {
    cookieStr += '; domain='+domain;
  } else {
    cookieStr += '; domain=.'+getTLD(location.hostname);
  }
  if (typeof expires === 'number') {
    cookieStr += '; expires='+expiresToStr(expires);
  }
  console.log('Setting cookie to "'+cookieStr+'"');
  document.cookie = cookieStr;
}

function deleteCookie(cookieName, path) {
  // Try carpet bombing approach to get cookie deleted, no matter how specific its domain.
  var subdomains = location.hostname.split('.');
  var domain = '.'+subdomains[subdomains.length-1];
  var domains = [];
  for (var i = subdomains.length-2; i >= 0; i--) {
    domain = subdomains[i] + domain;
    domains.unshift(domain);
    domain = '.' + domain;
    domains.unshift(domain);
  }
  for (var i = 0; i < domains.length; i++) {
    setCookie(cookieName, '', path, domains[i], -1);
  }
}

function expiresToStr(years) {
  var date = new Date();
  date.setTime(date.getTime()+(years*365.2425*24*60*60*1000));
  return date.toUTCString();
}

function getTLD(domain) {
  // "test.nstoler.com" -> "nstoler.com"
  // "localhost" -> "localhost"
  // "bbc.co.uk" -> "co.uk" :(
  var subdomains = domain.split('.');
  var n = subdomains.length;
  if (n == 1) {
    return domain;
  } else {
    return subdomains[n-2]+'.'+subdomains[n-1];
  }
}

main();
