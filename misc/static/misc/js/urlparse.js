'use strict';

// Common tracking/analytics query parameters (matched case-insensitively).
// These are deselected by default, and are what the "all but tracking" preset removes.
var TRACKING_PARAMS = new Set([
  // Google Analytics / Google Ads.
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id',
  'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
  'gclid', 'gclsrc', 'dclid', 'gbraid', 'wbraid', '_ga', '_gl',
  // Other ad networks.
  'fbclid', 'msclkid', 'twclid', 'ttclid', 'yclid', 'srsltid',
  // Email marketing platforms.
  'mc_cid', 'mc_eid', 'mkt_tok', 'vero_id', 'vero_conv',
  '_hsenc', '_hsmi', '__hssc', '__hstc', '__hsfp',
  // Social/referral sharing.
  'igshid', 'igsh', 'igsi', 'ref', 'ref_src', 'ref_url', 'si', 'spm', 'scid', 'ncid', 'cndid',
  // Misc analytics.
  'oly_anon_id', 'oly_enc_id', 'epik', 'guccounter', 'guce_referrer', 'guce_referrer_sig',
  'pk_campaign', 'pk_kwd', 'pk_source', 'pk_medium', 'pk_content', 'trk', 'trkcampaign', 's_cid',
]);

// The currently parsed query parameters: {key, value, selected}, in the order they appear in the url.
var params = [];

function main() {
  var originalUrlInput = document.querySelector('#originalUrl');
  originalUrlInput.addEventListener('input', parseAndRender);
  document.querySelector('#selectAll').addEventListener('click', function() { setAllSelected(true); });
  document.querySelector('#selectNone').addEventListener('click', function() { setAllSelected(false); });
  document.querySelector('#selectNoTracking').addEventListener('click', selectAllButTracking);
  document.querySelector('#copyButton').addEventListener('click', copyEditedUrl);
  // Parse whatever is already in the box on load (e.g. from the `url` query parameter).
  parseAndRender();
}

// Grows/shrinks a textarea's height to fit its content, so wrapped urls are fully visible.
function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
}

// Re-reads the original url box, rebuilds the parameter list from scratch, and redraws everything.
// The parameter table's selection state is intentionally not preserved across this, since a change
// to the original url is treated as a fresh url to work with.
function parseAndRender() {
  var originalUrlInput = document.querySelector('#originalUrl');
  autoResizeTextarea(originalUrlInput);
  var urlStr = originalUrlInput.value.trim();
  var errorElement = document.querySelector('#urlError');
  var url = urlStr === '' ? null : parseUrl(urlStr);
  if (urlStr !== '' && url === null) {
    errorElement.textContent = 'Invalid url.';
  } else {
    errorElement.textContent = '';
  }
  params = [];
  if (url !== null) {
    for (var pair of url.searchParams.entries()) {
      var key = pair[0];
      var value = pair[1];
      params.push({key: key, value: value, selected: !isTrackingParam(key)});
    }
  }
  displayParams();
  updateEditedUrl(url);
}

function parseUrl(urlStr) {
  try {
    return new URL(urlStr);
  } catch (error) {
    return null;
  }
}

function isTrackingParam(key) {
  return TRACKING_PARAMS.has(key.toLowerCase());
}

function displayParams() {
  var tbody = document.querySelector('#paramsTable tbody');
  // First, delete all the existing rows.
  while (tbody.children.length > 0) {
    tbody.removeChild(tbody.children[0]);
  }
  // Then, add a row for each parameter.
  for (var i = 0; i < params.length; i++) {
    tbody.appendChild(makeParamRow(params[i], i));
  }
  var table = document.querySelector('#paramsTable');
  var noParamsMessage = document.querySelector('#noParamsMessage');
  if (params.length === 0) {
    table.style.display = 'none';
    noParamsMessage.style.display = 'block';
  } else {
    table.style.display = '';
    noParamsMessage.style.display = 'none';
  }
}

function makeParamRow(param, index) {
  var checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = param.selected;
  checkbox.addEventListener('change', function() {
    params[index].selected = checkbox.checked;
    updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
  });
  var checkboxCell = document.createElement('td');
  checkboxCell.appendChild(checkbox);
  // Let clicking anywhere in the cell toggle the checkbox, not just the tiny checkbox itself.
  checkboxCell.addEventListener('click', function(event) {
    if (event.target !== checkbox) {
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event('change'));
    }
  });

  var keyCell = document.createElement('td');
  keyCell.appendChild(document.createTextNode(param.key));

  var valueCell = document.createElement('td');
  valueCell.appendChild(document.createTextNode(param.value));

  var row = document.createElement('tr');
  row.appendChild(checkboxCell);
  row.appendChild(keyCell);
  row.appendChild(valueCell);
  return row;
}

function setAllSelected(selected) {
  for (var i = 0; i < params.length; i++) {
    params[i].selected = selected;
  }
  displayParams();
  updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
}

function selectAllButTracking() {
  for (var i = 0; i < params.length; i++) {
    params[i].selected = !isTrackingParam(params[i].key);
  }
  displayParams();
  updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
}

// Rebuilds the "Edited url" box from the currently selected parameters.
// `url` is the parsed original url (or null, if the original box is empty/invalid).
function updateEditedUrl(url) {
  var editedUrlInput = document.querySelector('#editedUrl');
  if (url === null) {
    editedUrlInput.value = '';
  } else {
    var query = new URLSearchParams();
    for (var i = 0; i < params.length; i++) {
      if (params[i].selected) {
        query.append(params[i].key, params[i].value);
      }
    }
    var queryStr = query.toString();
    editedUrlInput.value = url.origin + url.pathname + (queryStr ? '?'+queryStr : '') + url.hash;
  }
  autoResizeTextarea(editedUrlInput);
}

function copyEditedUrl() {
  var editedUrlInput = document.querySelector('#editedUrl');
  editedUrlInput.select();
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(editedUrlInput.value);
  } else {
    document.execCommand('copy');
  }
}

main();
