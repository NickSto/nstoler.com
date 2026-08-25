'use strict';

// Confirmed or likely tracking/analytics query parameters that aren't specific to a single site.
const GLOBAL_TRACKING_PARAMS = new Set([
  // Google Analytics / Google Ads.
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id', 'utm_name',
  'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic', 'utm_kxconfid',
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
  'link_id', 'can_id', 'email_referrer', 'email_subject', 'referrer', 'ref',
  'gad_campaignid', 'gad_source', 'tw_source', 'tw_adid', 'tw_campaign', 'tw_kwdid',
]);

// Query parameters that are only trackers on specific sites (they may be legitimate, functional
// parameters elsewhere). `domains` matches the url's hostname exactly or any of its subdomains.
const DOMAIN_TRACKING_PARAMS = [
  {domains: ['instagram.com'], params: ['igshid', 'igsh', 'igsi']},
  {domains: ['threads.com'], params: ['xmt', 'slof']},
  {domains: ['youtube.com', 'youtu.be'], params: ['si', 'is', 'pp', 'forigin']},
  {domains: ['twitter.com', 'x.com'], params: ['ref_src', 'ref_url', 's', 't']},
  {domains: ['facebook.com'], params: ['mibextid']},
  {domains: ['reddit.com'], params: ['share_id']},
  {domains: ['spotify.com'], params: ['si']},
  {domains: ['linkedin.com'], params: ['trk', 'trkemail', 'trackingid', 'refid', 'rcm']},
  {
    domains: ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de'],
    params: [
      'ref', 'ref_', 'tag', 'linkcode', 'creativeasin', 'psc',
      'pd_rd_r', 'pd_rd_w', 'pd_rd_wg', 'pf_rd_p', 'pf_rd_r', 'pf_rd_s', 'pf_rd_t', 'pf_rd_i',
    ]
  },
  {domains: ['patreon.com'], params: ['post_id', 'token']},
  {domains: ['yelp.com'], params: ['src_bizid', 's']},
  {domains: ['taobao.com', 'tmall.com', 'alibaba.com'], params: ['spm']},
  {domains: ['yahoo.com', 'aol.com'], params: ['ncid']},
  {domains: ['partiful.com'], params: ['c']},
  {domains: ['washingtonpost.com'], params: ['carta-url']},
  {domains: ['nytimes.com'], params: ['smid', 'referringSource', 'sgrp']},
  {domains: ['fandango.com'], params: ['ssid', 'rtm', 'lat', 'lon', 'rad', 'cmp']},
  {domains: ['wsj.com'], params: ['gaa_at', 'gaa_n', 'gaa_ts', 'gaa_sig']},
  {
    domains: [
      'condenast.com', 'wired.com', 'vogue.com', 'vanityfair.com', 'gq.com', 'newyorker.com',
      'architecturaldigest.com'
    ],
    params: ['cndid']
  },
  {
    domains: ['etsy.com'],
    params: [
      'ga_order', 'ga_search_type', 'ga_view_type', 'ga_search_query', 'ref', 'content_source',
      'organic_search_click', 'logging_key', 'click_key', 'click_sum'
    ]
  }
];

// The currently parsed query parameters: {key, value, selected}, in the order they appear in the url.
let params = [];

// The hostname of the last successfully parsed url.
let currentHostname = null;

function main() {
  const originalUrlInput = document.querySelector('#originalUrl');
  const errorElement = document.getElementById('urlError');
  originalUrlInput.addEventListener('input', parseAndRender);
  document.getElementById('selectAll').addEventListener('click', () => setAllSelected(true));
  document.getElementById('selectNone').addEventListener('click', () => setAllSelected(false));
  document.getElementById('selectNoTracking').addEventListener('click', selectAllButTracking);
  document.getElementById('goButton').addEventListener('click', (event) => {
    // The button is only a real link (with an href) once there's a valid edited url to go to.
    if (!event.currentTarget.hasAttribute('href')) {
      event.preventDefault();
    }
  });
  document.getElementById('copyButton').addEventListener('click', copyEditedUrl);
  document.getElementById('pasteButton').addEventListener('click', async () => {
    try {
      const url = await navigator.clipboard.readText();
      originalUrlInput.value = url;
      parseAndRender();
    } catch (error) {
      errorElement.textContent = 'Failed to read from clipboard: ' + error.message;
    }
  });
  document.getElementById('domainBox').addEventListener('input', (event) => {
    const newDomain = event.currentTarget.value.trim() || null;
    //TODO: Validate that it's a valid domain.
    if (newDomain === '') {
      return;
    }
    let url = parseUrl(originalUrlInput.value.trim());
    if (url === null) {
      return;
    }
    url.hostname = newDomain;
    updateEditedUrl(url);
  });
  // The step button is only rendered in the template for the admin.
  const stepButton = document.getElementById('stepButton');
  if (stepButton) {
    stepButton.addEventListener('click', stepForward);
  }
  // Parse whatever is already in the box on load (e.g. from the `url` query parameter).
  parseAndRender();
}

// Grows/shrinks a textarea's height to fit its content, so wrapped urls are fully visible.
function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
}

// Asks the server to take one step in the original url's redirect chain (admin-only), and if it
// finds one, replaces the original url with it (so the user can inspect or edit it before the
// next step). Leaves the url alone if it's already the final destination, or on error.
async function stepForward() {
  const originalUrlInput = document.getElementById('originalUrl');
  const stepButton = document.getElementById('stepButton');
  const stepStatus = document.getElementById('stepStatus');
  const urlStr = originalUrlInput.value.trim();
  if (!urlStr) {
    stepStatus.textContent = 'Enter a url first.';
    return;
  }
  stepButton.disabled = true;
  stepStatus.textContent = 'Checking\u2026';
  try {
    const response = await fetch(`/misc/urltools/resolve?url=${encodeURIComponent(urlStr)}&via=js`);
    const data = await response.json();
    if (!response.ok) {
      stepStatus.textContent = `Error: ${data.error || response.statusText}`;
    } else if (data.location) {
      originalUrlInput.value = data.location;
      parseAndRender();
      if (data.type === 'refresh') {
        stepStatus.textContent = `Redirected via a <meta refresh> (status ${data.code}).`;
      } else {
        stepStatus.textContent = `Redirected via a ${data.code} (${data.type}).`;
      }
    } else {
      stepStatus.textContent = `No further redirect (status ${data.code}). This is the final destination.`;
    }
  } catch (error) {
    stepStatus.textContent = `Error: ${error.message}`;
  } finally {
    stepButton.disabled = false;
  }
}

// Re-reads the original url box, rebuilds the parameter list from scratch, and redraws everything.
// The parameter table's selection state is intentionally not preserved across this, since a change
// to the original url is treated as a fresh url to work with.
function parseAndRender() {
  const originalUrlInput = document.getElementById('originalUrl');
  autoResizeTextarea(originalUrlInput);
  const domainBox = document.getElementById('domainBox');
  const urlStr = originalUrlInput.value.trim();
  const errorElement = document.getElementById('urlError');
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
    domainBox.value = currentHostname;
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
  const table = document.getElementById('paramsTable');
  const noParamsMessage = document.getElementById('noParamsMessage');
  if (params.length === 0) {
    table.style.display = 'none';
    noParamsMessage.style.display = 'block';
  } else {
    table.style.display = 'table';
    noParamsMessage.style.display = 'none';
  }
}

function makeParamRow(param, index) {
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = param.selected;
  checkbox.addEventListener('change', () => {
    params[index].selected = checkbox.checked;
    updateEditedUrl(parseUrl(document.getElementById('originalUrl').value.trim()));
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
  updateEditedUrl(parseUrl(document.getElementById('originalUrl').value.trim()));
}

function selectAllButTracking() {
  for (const param of params) {
    param.selected = !isTrackingParam(param.key, currentHostname);
  }
  displayParams();
  updateEditedUrl(parseUrl(document.getElementById('originalUrl').value.trim()));
}

// Rebuilds the "Edited url" box from the currently selected parameters.
// `url` is the parsed original url (or null, if the original box is empty/invalid).
function updateEditedUrl(url) {
  const editedUrlInput = document.getElementById('editedUrl');
  if (url === null) {
    editedUrlInput.value = '';
    updateGoButton(null);
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
    const editedUrlStr = url.origin + url.pathname + queryPart + url.hash;
    editedUrlInput.value = editedUrlStr;
    updateGoButton(editedUrlStr);
  }
  autoResizeTextarea(editedUrlInput);
}

// Keeps the "Go" button's target in sync with the edited url, disabling it when there isn't one.
function updateGoButton(editedUrlStr) {
  const goButton = document.getElementById('goButton');
  if (editedUrlStr === null) {
    goButton.removeAttribute('href');
    goButton.classList.add('disabled');
  } else {
    goButton.href = editedUrlStr;
    goButton.classList.remove('disabled');
  }
}

function copyEditedUrl() {
  const editedUrlInput = document.getElementById('editedUrl');
  editedUrlInput.select();
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(editedUrlInput.value);
  } else {
    document.execCommand('copy');
  }
}

main();
