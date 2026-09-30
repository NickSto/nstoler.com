'use strict';

// GitHub caches raw gists for about 5 minutes, so edits to the gist take that long to show up.
const GIST_URL = 'https://gist.githubusercontent.com/NickSto/9b1c2d7ba2ad7187c1f35a51bba3d85e/raw/tracking-params.json';
const GIST_TIMEOUT_MS = 3000;
// The repo's copy of the gist. Often out of date, since it only updates when I push.
const LOCAL_PARAMS_URL = document.currentScript.dataset.localParamsUrl;

/* The list of all known tracking parameters (loaded at startup).
 * `global` is a Set of query parameters that are trackers on any site.
 * `sites` are parameters which are only considered trackers if they appear on specific sites
 *   (they may be legitimate, functional parameters on other sites).
 *   The structure: a list of {domains, params}, where each domain in `domains` may match the url's
 *   hostname exactly or any subdomain.
 */
//TODO: Use the extensive AdGuard filters as a source of tracking parameters:
//      https://github.com/AdguardTeam/AdguardFilters/tree/master/TrackParamFilter/sections
//TODO: This page refers to a lot of other tools that do this. Investigate:
//      https://github.com/jparise/chrome-utm-stripper
let trackingParams = {global: new Set(), sites: []};

/*TODO: Find a way to handle certain parameters which are too generic to strip indiscriminately.
 *      For example, the tracking-query-params-registry lists two parameters they think are Adobe's:
 *      `cid` and `sid`. These are probably too short to safely remove from everything, but may be
 *      used the same as other global trackers. But the registry notes that these are usually
 *      combined with other tracking parameters, leading to the possibility of only removing them
 *      when present in certain combinations. Others like this: `kb`, `adid`, `adgroupid`, `adtype`.
 */
//TODO: Break the site-specific parameters down further by path. For example, on Youtube, `v` is a
//      necessary parameter on `/watch`, but a tracker on `/redirect`.

// The currently parsed query parameters: {key, value, selected}, in the order they appear in the url.
let params = [];

// The hostname of the last successfully parsed url.
let currentHostname = null;

// Fetches the tracking parameters from the gist, falling back to the copy on this site.
// Throws if both fail.
async function loadTrackingParams() {
  try {
    const gistOptions = {
      signal: AbortSignal.timeout(GIST_TIMEOUT_MS),
      referrerPolicy: 'no-referrer',
      credentials: 'omit',
    };
    return await fetchTrackingParams(GIST_URL, gistOptions);
  } catch (error) {
    console.warn('Failed to load tracking parameters from the gist:', error);
  }
  return await fetchTrackingParams(LOCAL_PARAMS_URL + '?via=js', {});
}

async function fetchTrackingParams(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }
  return parseTrackingParams(await response.json());
}

// Validates the JSON structure and flattens the sections of global parameters into one Set.
function parseTrackingParams(data) {
  if (!Array.isArray(data?.global) || !Array.isArray(data?.sites)) {
    throw new Error('Expected "global" and "sites" lists.');
  }
  const globalParams = new Set();
  for (const section of data.global) {
    requireStringArray(section?.params, 'params of a global section');
    for (const param of section.params) {
      globalParams.add(param);
    }
  }
  for (const rule of data.sites) {
    requireStringArray(rule?.domains, 'domains of a site rule');
    requireStringArray(rule?.params, 'params of a site rule');
  }
  return {global: globalParams, sites: data.sites};
}

function requireStringArray(value, description) {
  if (!Array.isArray(value) || !value.every((item) => typeof item === 'string')) {
    throw new Error(`Expected the ${description} to be a list of strings.`);
  }
}

async function main() {
  try {
    trackingParams = await loadTrackingParams();
  } catch (error) {
    document.getElementById('paramsError').textContent =
      `Error: Failed to load the list of tracking parameters (${error.message}). ` +
      'No parameters will be recognized as tracking.';
  }
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
  if (trackingParams.global.has(key)) {
    return true;
  }
  for (const rule of trackingParams.sites) {
    if (!rule.params.includes(key)) {
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
  const lowerDomain = domain.toLowerCase();
  return lowerHostname === lowerDomain || lowerHostname.endsWith('.'+lowerDomain);
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
