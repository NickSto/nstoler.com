'use strict';

// Tracking/analytics query parameters that are always trackers, regardless of which site the url
// points to (matched case-insensitively). These are deselected by default, and are what the
// "all but tracking" preset removes.
var GLOBAL_TRACKING_PARAMS = new Set([
  // Google Analytics / Google Ads.
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id', 'utm_name',
  'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
  'gclid', 'gclsrc', 'dclid', 'gbraid', 'wbraid', '_ga', '_gl',
  // Other ad networks.
  'fbclid', 'msclkid', 'twclid', 'ttclid', 'yclid', 'srsltid',
  // Email marketing platforms.
  'mc_cid', 'mc_eid', 'mkt_tok', 'vero_id', 'vero_conv',
  '_hsenc', '_hsmi', '__hssc', '__hstc', '__hsfp',
  // Misc analytics, added to the destination url regardless of what site it points to.
  'oly_anon_id', 'oly_enc_id', 'epik', 'guccounter', 'guce_referrer', 'guce_referrer_sig',
  'pk_campaign', 'pk_kwd', 'pk_source', 'pk_medium', 'pk_content', 's_cid', 'scid',
  // Unknown
  'gad_campaignid', 'gad_source', 'tw_source', 'tw_adid', 'tw_campaign', 'tw_kwdid'
]);

// Query parameters that are only trackers on specific sites (they may be legitimate, functional
// parameters elsewhere). `domains` matches the url's hostname exactly or any of its subdomains.
var DOMAIN_TRACKING_PARAMS = [
  {domains: ['instagram.com'], params: ['igshid', 'igsh', 'igsi']},
  {domains: ['threads.com'], params: ['xmt', 'slof']},
  {domains: ['youtube.com', 'youtu.be'], params: ['si']},
  {domains: ['spotify.com'], params: ['si']},
  {domains: ['twitter.com', 'x.com'], params: ['ref_src', 'ref_url', 's', 't']},
  {domains: ['reddit.com'], params: ['share_id']},
  {domains: ['linkedin.com'], params: ['trk', 'trkemail', 'trackingid', 'refid']},
  {
    domains: ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de'],
    params: [
      'ref', 'ref_', 'tag', 'linkcode', 'creativeasin', 'psc',
      'pd_rd_r', 'pd_rd_w', 'pd_rd_wg', 'pf_rd_p', 'pf_rd_r', 'pf_rd_s', 'pf_rd_t', 'pf_rd_i',
    ]
  },
  {domains: ['taobao.com', 'tmall.com', 'alibaba.com'], params: ['spm']},
  {domains: ['yahoo.com', 'aol.com'], params: ['ncid']},
  {
    domains: [
      'condenast.com', 'wired.com', 'vogue.com', 'vanityfair.com', 'gq.com', 'newyorker.com',
      'architecturaldigest.com'
    ],
    params: ['cndid']
  }
];

// The currently parsed query parameters: {key, value, selected}, in the order they appear in the url.
var params = [];

// The hostname of the last successfully parsed url, used to apply domain-specific tracking rules.
var currentHostname = null;

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
  currentHostname = url === null ? null : url.hostname;
  params = [];
  if (url !== null) {
    for (var pair of url.searchParams.entries()) {
      var key = pair[0];
      var value = pair[1];
      params.push({key: key, value: value, selected: !isTrackingParam(key, currentHostname)});
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

// `hostname` is the hostname of the url the parameter came from (or null, if unknown).
function isTrackingParam(key, hostname) {
  var lowerKey = key.toLowerCase();
  if (GLOBAL_TRACKING_PARAMS.has(lowerKey)) {
    return true;
  }
  for (var i = 0; i < DOMAIN_TRACKING_PARAMS.length; i++) {
    var rule = DOMAIN_TRACKING_PARAMS[i];
    if (rule.params.indexOf(lowerKey) === -1) {
      continue;
    }
    for (var j = 0; j < rule.domains.length; j++) {
      if (hostnameMatchesDomain(hostname, rule.domains[j])) {
        return true;
      }
    }
  }
  return false;
}

// True if `hostname` is exactly `domain`, or a subdomain of it.
function hostnameMatchesDomain(hostname, domain) {
  if (!hostname) {
    return false;
  }
  hostname = hostname.toLowerCase();
  return hostname === domain || hostname.endsWith('.'+domain);
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
    params[i].selected = !isTrackingParam(params[i].key, currentHostname);
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
