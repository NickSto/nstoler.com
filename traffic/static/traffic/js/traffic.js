
function trafficMain() {
  var brunnerElem = document.getElementById('brunner');
  if (brunnerElem === null) {
    return;
  }
  var jsEnabledElem = document.querySelector('input[name="jsEnabled"]');
  jsEnabledElem.value = 'True';
  var gridAutofilledElem = document.querySelector('input[name="gridAutofilled"]');
  solveGrid(brunnerElem);
  gridAutofilledElem.value = 'True';
}

function solveGrid(brunnerElem) {
  var solution = [3, 5, 7];
  for (var i = 0; i < solution.length; i++) {
    var boxNum = solution[i];
    var boxElem = document.createElement('input');
    boxElem.style.display = 'none';
    boxElem.type = 'checkbox';
    boxElem.name = 'brunner:check'+boxNum;
    boxElem.checked = true;
    brunnerElem.appendChild(boxElem);
  }
}

window.addEventListener('load', trafficMain, false);
