
const PROPERTIES = {
  screen: {
    'window.screen.width': {fxn:() => window.screen.width, type:'eventless'},
    'window.screen.height': {fxn:() => window.screen.height, type:'eventless'},
    'window.outerWidth': {fxn:() => window.outerWidth, type:'eventless'},
    'window.outerHeight': {fxn:() => window.outerHeight, type:'eventless'},
    'window.innerWidth': {fxn:() => window.innerWidth, type:'eventless'},
    'window.innerHeight': {fxn:() => window.innerHeight, type:'eventless'},
  },
  scroll: {
    'window.scrollX': {fxn:() => window.scrollX, type:'eventless'},
    'window.scrollY': {fxn:() => window.scrollY, type:'eventless'},
  },
  mousemove: {
    'mousemove.pageX': {fxn: (event) => event.pageX, type:'event'},
    'mousemove.pageY': {fxn: (event) => event.pageY, type:'event'},
    'mousemove.clientX': {fxn: (event) => event.clientX, type:'event'},
    'mousemove.clientY': {fxn: (event) => event.clientY, type:'event'},
    'mousemove.screenX': {fxn: (event) => event.screenX, type:'event'},
    'mousemove.screenY': {fxn: (event) => event.screenY, type:'event'},
  },
  click: {
    'click.pageX': {fxn: (event) => event.pageX, type:'event'},
    'click.pageY': {fxn: (event) => event.pageY, type:'event'},
    'click.clientX': {fxn: (event) => event.clientX, type:'event'},
    'click.clientY': {fxn: (event) => event.clientY, type:'event'},
    'click.screenX': {fxn: (event) => event.screenX, type:'event'},
    'click.screenY': {fxn: (event) => event.screenY, type:'event'},
    'click.detail': {fxn: (event) => event.detail, type:'event'},
    'click.target': {fxn: (event) => event.target.tagName, type:'event'},
  },
}

function main() {
  let dataList = document.getElementById('dataList');
  for (const domain in PROPERTIES) {
    for (const property in PROPERTIES[domain]) {
      let propertyMeta = PROPERTIES[domain][property];
      const [rowElem, displayElem] = createRow(property);
      dataList.appendChild(rowElem);
      if (propertyMeta.type === 'eventless') {
        displayElem.textContent = propertyMeta.fxn();
      }
      propertyMeta.displayElem = displayElem;
    }
  }
  document.addEventListener('scroll', updateData);
  document.addEventListener('mousemove', updateData);
  document.addEventListener('click', updateData);
}

function createRow(label) {
  let rowElem = document.createElement('tr');
  let labelElem = document.createElement('td');
  labelElem.textContent = label;
  let displayElem = document.createElement('td');
  rowElem.appendChild(labelElem);
  rowElem.appendChild(displayElem);
  return [rowElem, displayElem];
}

//TODO: Throttle mousemove and scroll events as described here:
//      https://www.html5rocks.com/en/tutorials/speed/animations/

//TODO: Safari Mobile might not register click events on some elements:
//      https://developer.mozilla.org/en-US/docs/Web/API/Element/click_event#Safari_Mobile

function updateData(event) {
  const domainMeta = PROPERTIES[event.type];
  for (const property in domainMeta) {
    let propertyMeta = domainMeta[property];
    propertyMeta.displayElem.textContent = propertyMeta.fxn(event);
  }
}

window.addEventListener('load', main, false);
