
function mainMain() {
  var buttonElem = document.getElementById('navbar-button');
  var navbarElem = document.getElementById('navbar-collapse');
  buttonElem.addEventListener('click', function() {toggleNavbar(navbarElem);});
}

function toggleNavbar(navbarElem) {
  if (navbarElem.classList.contains('collapse')) {
    navbarElem.classList.remove('collapse');
  } else {
    navbarElem.classList.add('collapse');
  }
}

window.addEventListener('load', mainMain, false);
