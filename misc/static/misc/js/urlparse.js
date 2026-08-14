'use strict';

// Tracking/analytics query parameters that are always trackers, regardless of which site the url
// points to (matched case-insensitively). These are deselected by default, and are what the
// "all but tracking" preset removes.
const GLOBAL_TRACKING_PARAMS = new Set([
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
const DOMAIN_TRACKING_PARAMS = [
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
let params = [];

// The hostname of the last successfully parsed url, used to apply domain-specific tracking rules.
let currentHostname = null;

function main() {
  const originalUrlInput = document.querySelector('#originalUrl');
  originalUrlInput.addEventListener('input', parseAndRender);
  document.querySelector('#selectAll').addEventListener('click', () => setAllSelected(true));
  document.querySelector('#selectNone').addEventListener('click', () => setAllSelected(false));
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
  const originalUrlInput = document.querySelector('#originalUrl');
  autoResizeTextarea(originalUrlInput);
  const urlStr = originalUrlInput.value.trim();
  const errorElement = document.querySelector('#urlError');
  let url = null;
  if (urlStr !== '') {
    url = parseUrl(urlStr);
  }
  if (urlStr !== '' && url === null) {
    errorElement.textContent = 'Invalid url.';
  } else {
    errorElement.textContent = '';
  }
  if (url === null) {
    currentHostname = null;
  } else {
    currentHostname = url.hostname;
  }
  params = [];
  if (url !== null) {
    for (const [key, value] of url.searchParams.entries()) {
      params.push({key, value, selected: !isTrackingParam(key, currentHostname)});
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
  const lowerKey = key.toLowerCase();
  if (GLOBAL_TRACKING_PARAMS.has(lowerKey)) {
    return true;
  }
  for (const rule of DOMAIN_TRACKING_PARAMS) {
    if (!rule.params.includes(lowerKey)) {
      continue;
    }
    for (const domain of rule.domains) {
      if (hostnameMatchesDomain(hostname, domain)) {
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
  const lowerHostname = hostname.toLowerCase();
  return lowerHostname === domain || lowerHostname.endsWith('.'+domain);
}

function displayParams() {
  const tbody = document.querySelector('#paramsTable tbody');
  // First, delete all the existing rows.
  while (tbody.children.length > 0) {
    tbody.removeChild(tbody.children[0]);
  }
  // Then, add a row for each parameter.
  for (const [index, param] of params.entries()) {
    tbody.appendChild(makeParamRow(param, index));
  }
  const table = document.querySelector('#paramsTable');
  const noParamsMessage = document.querySelector('#noParamsMessage');
  if (params.length === 0) {
    table.style.display = 'none';
    noParamsMessage.style.display = 'block';
  } else {
    table.style.display = '';
    noParamsMessage.style.display = 'none';
  }
}

function makeParamRow(param, index) {
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = param.selected;
  checkbox.addEventListener('change', () => {
    params[index].selected = checkbox.checked;
    updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
  });
  const checkboxCell = document.createElement('td');
  checkboxCell.appendChild(checkbox);
  // Let clicking anywhere in the cell toggle the checkbox, not just the tiny checkbox itself.
  checkboxCell.addEventListener('click', (event) => {
    if (event.target !== checkbox) {
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event('change'));
    }
  });

  const keyCell = document.createElement('td');
  keyCell.appendChild(document.createTextNode(param.key));

  const valueCell = document.createElement('td');
  valueCell.appendChild(document.createTextNode(param.value));

  const row = document.createElement('tr');
  row.appendChild(checkboxCell);
  row.appendChild(keyCell);
  row.appendChild(valueCell);
  return row;
}

function setAllSelected(selected) {
  for (const param of params) {
    param.selected = selected;
  }
  displayParams();
  updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
}

function selectAllButTracking() {
  for (const param of params) {
    param.selected = !isTrackingParam(param.key, currentHostname);
  }
  displayParams();
  updateEditedUrl(parseUrl(document.querySelector('#originalUrl').value.trim()));
}

// Rebuilds the "Edited url" box from the currently selected parameters.
// `url` is the parsed original url (or null, if the original box is empty/invalid).
function updateEditedUrl(url) {
  const editedUrlInput = document.querySelector('#editedUrl');
  if (url === null) {
    editedUrlInput.value = '';
  } else {
    const query = new URLSearchParams();
    for (const param of params) {
      if (param.selected) {
        query.append(param.key, param.value);
      }
    }
    const queryStr = query.toString();
    let queryPart = '';
    if (queryStr) {
      queryPart = '?'+queryStr;
    }
    editedUrlInput.value = url.origin + url.pathname + queryPart + url.hash;
  }
  autoResizeTextarea(editedUrlInput);
}

function copyEditedUrl() {
  const editedUrlInput = document.querySelector('#editedUrl');
  editedUrlInput.select();
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(editedUrlInput.value);
  } else {
    document.execCommand('copy');
  }
}

main();
