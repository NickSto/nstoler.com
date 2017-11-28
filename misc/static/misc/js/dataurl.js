
function toDataUrl() {
  var fileInput = document.getElementById('selection');

  // files is a FileList object (similar to NodeList)
  var files = fileInput.files;

  if (files.length === 0) {
    alert('No file selected!');
    return;
  }

  if (files[0].size > 100000) {
    alert('File too big! Must be smaller than 100000 bytes.');
    return;
  }

  var reader = new FileReader();
  reader.onloadend = function() {
    var resultBox = document.getElementById('resultBox');
    resultBox.textContent = reader.result;
    var result = document.getElementById('result');
    result.style.display = 'inherit';
  };

  reader.readAsDataURL(files[0]);
}

document.getElementById('submit').onclick = toDataUrl;
