function parseSession() {
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
      log('error', 'file is the wrong length (expected 5 lines).');
      return;
    }
    try {
      var sessionData = JSON.parse(fileLines[4]);
    } catch (SyntaxError) {
      log('error', 'invalid data in file. Maybe it\'s not a Session Manager session?');
      return;
    }
    if (sessionData.windows === undefined || sessionData.windows.length < 1) {
      log('error', 'session data not as expected.');
      return;
    }

    var windowList = [];
    for (var w = 0; w < sessionData.windows.length; w++) {
      var sWindow = sessionData.windows[w];
      if (sWindow.tabs === undefined || sWindow.tabs.length < 1) {
        log('warning', 'session data not as expected (in the window object).');
        continue;
      }
      console.log('Window '+(w+1)+': '+sWindow.tabs.length+' tabs');
      var tabList = [];
      for (var t = 0; t < sWindow.tabs.length; t++) {
        var tab = sWindow.tabs[t];
        if (tab.entries === undefined || tab.entries.length < 1) {
          log('warning', 'session data not as expected (in the tab object).');
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
    displaySession(windowList);
  };

  reader.readAsText(files[0]);
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

function log(level, message) {
  var stderr = document.getElementById('stderr');
  var line = document.createElement('p');
  if (level) {
    var text = level[0].toUpperCase()+level.slice(1)+': '+message;
  } else {
    var text = message;
  }
  var textNode = document.createTextNode(text);
  line.appendChild(textNode);
  stderr.appendChild(line);
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

document.getElementById('submit').onclick = parseSession;
