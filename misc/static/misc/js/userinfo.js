'user strict';

function main() {
  var screenData = getResolution();
  updateTable(screenData);
}

function getResolution() {
  return {
    width: window.screen.width,
    height: window.screen.height,
  };
}

function updateTable(data) {
  var table = document.getElementById("data");
  var done = {};
  // Find any existing rows for these keys and update them.
  for (var i = 0; i < table.children.length; i++) {
    var row = table.children[i];
    if (row.children.length != 2) {
      continue;
    }
    var keyField = row.children[0];
    var valueField = row.children[1];
    var key = keyField.textContent;
    if (data.hasOwnProperty(key)) {
      valueField.textContent = data[key];
      done[key] = true;
    }
  }
  // Create new rows that don't exist yet.
  var keys = Object.keys(data);
  for (var i = 0; i < keys.length; i++) {
    var key = keys[i];
    if (done[key]) {
      continue;
    }
    var row = document.createElement("tr");
    var keyField = document.createElement("td");
    keyField.className = "name";
    keyField.textContent = key;
    var valueField = document.createElement("td");
    valueField.className = "value";
    valueField.textContent = data[key];
    row.appendChild(keyField);
    row.appendChild(valueField);
    table.appendChild(row);
  }
}

window.addEventListener('load', main, false);
