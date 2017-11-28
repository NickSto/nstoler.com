var windowList;

function readSession() {
  deleteChildren(document.getElementById('stderr'));
  deleteChildren(document.getElementById('session'));

  var fileInput = document.getElementById('selection');

  // files is a FileList object (similar to NodeList)
  var files = fileInput.files;

  if (files.length === 0) {
    log('error', 'No file selected!');
    return;
  } else if (files.length > 1) {
    log('error', 'Please select only 1 file.');
    return;
  }

  var reader = new FileReader();
  reader.onloadend = function() {
    // Line ending fix needed because of Firefox bug:
    // https://stackoverflow.com/questions/18898036/how-to-keep-newline-characters-when-i-import-a-javascript-file-with-filereader
    var fileContents = reader.result.replace(/\r/g, "\n");
    var fileLines = fileContents.split("\n");
    if (fileLines.length !== 5) {
      log('error', 'File is the wrong length (expected 5 lines).');
      return;
    }
    try {
      var sessionData = JSON.parse(fileLines[4]);
    } catch (SyntaxError) {
      log('error', 'Invalid data in file. Maybe it\'s not a Session Manager session?');
      return;
    }

    windowList = parseSessionData(sessionData);

    if (windowList !== undefined) {
      displaySession(windowList);
      var afterElement = document.getElementById('after-parsing');
      afterElement.style.display = 'inherit';
    }
  };

  reader.readAsText(files[0]);
}


function parseSessionData(data) {
  var windowList = [];

  if (data.windows === undefined || data.windows.length < 1) {
    log('error', 'Session data not as expected (missing "windows").');
    return;
  }

  for (var w = 0; w < data.windows.length; w++) {
    var sWindow = data.windows[w];
    if (sWindow.tabs === undefined || sWindow.tabs.length < 1) {
      log('warning', 'Session data not as expected (in the window object).');
      continue;
    }
    // Log everything to the console as a last-resort way to get some data if something goes wrong.
    console.log('Window '+(w+1)+': '+sWindow.tabs.length+' tabs');
    var tabList = [];
    for (var t = 0; t < sWindow.tabs.length; t++) {
      var tab = sWindow.tabs[t];
      if (tab.entries === undefined || tab.entries.length < 1) {
        log('warning', 'Session data not as expected (in the tab object).');
        continue;
      }
      var lastEntry = tab.entries[tab.entries.length-1];
      console.log('  '+lastEntry.title);
      console.log('    '+lastEntry.url);
      tabList.push(lastEntry);
    }
    console.log('');
    windowList.push(tabList);
  }

  return windowList;
}


function displaySession(windowList) {
  var sessionElement = document.getElementById('session');
  for (var w = 0; w < windowList.length; w++) {
    var tabList = windowList[w];
    var windowElement = document.createElement('div');
    var windowHeading = document.createElement('h4');
    var text = document.createTextNode('Window '+(w+1)+': '+tabList.length+' tabs');
    windowHeading.appendChild(text);
    windowElement.appendChild(windowHeading);
    for (var t = 0; t < tabList.length; t++) {
      var tab = tabList[t];
      var tabElement = document.createElement('p');
      var anchor = document.createElement('a');
      anchor.setAttribute('href', tab.url);
      if (tab.title === undefined) {
        var title = tab.url;
      } else {
        var title = tab.title;
      }
      var text = document.createTextNode(title);
      anchor.appendChild(text);
      tabElement.appendChild(anchor);
      windowElement.appendChild(tabElement);
    }
    sessionElement.appendChild(windowElement);
  }
}


function downloadSession() {
  if (windowList === undefined) {
    log('error', 'Please select a session file and click "Read session" first.');
    return;
  } else if (windowList.length < 1) {
    log('error', 'No data to download.');
    return;
  }
  var fileInput = document.getElementById('selection');
  var files = fileInput.files;
  if (files.length === 0) {
    log('error', 'No file selected!');
    return;
  }
  var filename = createFileName(files[0].name);
  var contents = createSessionFile(windowList);
  var link = document.createElement('a');
  link.setAttribute('href', 'data:text/plain;charset=utf-8,'+encodeURIComponent(contents));
  link.setAttribute('download', filename);
  var click = new MouseEvent('click');
  link.dispatchEvent(click);
}


function createSessionFile(windowList) {
  var contents = "";
  for (var w = 0; w < windowList.length; w++) {
    var tabList = windowList[w];
    contents += 'Window '+(w+1)+': '+tabList.length+' tabs\r\n';
    for (var t = 0; t < tabList.length; t++) {
      var tab = tabList[t];
      contents += '  '+tab.title+'\r\n';
      contents += '    '+tab.url+'\r\n';
    }
    contents += '\r\n';
  }
  return contents;
}


function createFileName(inputName) {
  var extStart = inputName.indexOf('.session');
  if (extStart == -1) {
    var base = inputName;
  } else {
    var base = inputName.slice(0, extStart);
  }
  return base + '.txt';
}


function log(level, message) {
  var stderr = document.getElementById('stderr');
  var line = document.createElement('p');
  if (level) {
    var text = capitalize(level)+': ';
  } else {
    var text = '';
  }
  text += capitalize(message);
  var textNode = document.createTextNode(text);
  line.appendChild(textNode);
  stderr.appendChild(line);
}


function capitalize(str) {
  return str[0].toUpperCase() + str.slice(1);
}


function deleteChildren(element) {
  if (element === null) {
    console.log('Error: Non-existent element.');
  } else {
    for (var i = 0; i < element.children.length; i++) {
      element.children[i].remove();
    }
  }
}


function init() {
  var afterElement = document.getElementById('after-parsing');
  afterElement.style.display = 'none';
  document.getElementById('submit').onclick = readSession;
  document.getElementById('download').onclick = downloadSession;
}

window.onload = init;
