
function trafficMain() {
  const brunnerElem = document.getElementById('brunner');
  if (brunnerElem === null) {
    return;
  }
  const jsEnabledElem = document.querySelector('input[name="jsEnabled"]');
  jsEnabledElem.value = 'True';
  solveGrid(brunnerElem);
}

function solveGrid(brunnerElem) {
  const solution = [3, 5, 7];
  for (let i in solution) {
    let boxNum = solution[i];
    let boxElem = document.createElement('input');
    boxElem.style.display = 'none';
    boxElem.type = 'checkbox';
    boxElem.name = 'brunner:check'+boxNum;
    boxElem.checked = true;
    brunnerElem.appendChild(boxElem);
  }
}

window.addEventListener('load', trafficMain, false);
