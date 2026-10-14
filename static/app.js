'use strict';

// Writes use POST forms; background reads update only changed DOM nodes.
const liveScene = document.querySelector('[data-live-scene]');
if (liveScene) {
  const plaza = liveScene.querySelector('[data-plaza]');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const status = document.querySelector('[data-sync-status]');
  const syncNow = document.querySelector('[data-sync-now]');
  const reload = document.querySelector('[data-sync-reload]');
  let selected = plaza.dataset.focus;
  let draggedForm = null;
  let pointerDown = false;
  let submitting = false;
  let stopped = false;
  let pending = null;
  let lastScroll = 0;

  function select(root, value) {
    root.querySelectorAll('[data-select]').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.select === value)));
    root.querySelectorAll('[data-detail]').forEach(panel => { panel.hidden = panel.dataset.detail !== value; });
  }

  function animate(choice, kind) {
    if (!choice || reducedMotion.matches) return;
    const animation = choice.dataset.select === 'public' ? 'arriving' : kind === 'arrive' ? 'vehicle-arriving' : 'boarding';
    choice.classList.remove('arriving', 'vehicle-arriving', 'boarding');
    void choice.offsetWidth;
    choice.classList.add(animation);
  }

  liveScene.addEventListener('click', event => {
    const choice = event.target.closest('[data-select]');
    if (!choice) return;
    selected = choice.dataset.select;
    select(plaza, selected);
    const url = new URL(window.location.href);
    url.searchParams.set('focus', selected);
    window.history.replaceState(null, '', url);
    if (selected === 'public') animate(choice, 'arrive');
    if (window.matchMedia('(max-width: 900px)').matches) {
      plaza.querySelector('.selection-panel').scrollIntoView({ block: 'nearest', behavior: reducedMotion.matches ? 'auto' : 'smooth' });
    }
  });

  if (plaza.dataset.motion) {
    const target = [...plaza.querySelectorAll('[data-select]')].find(choice => choice.dataset.select === plaza.dataset.motionTarget);
    animate(target, plaza.dataset.motion);
  }
  liveScene.addEventListener('animationend', event => {
    event.target.closest('[data-select]')?.classList.remove('arriving', 'vehicle-arriving', 'boarding');
  });

  // Dragging and the accessible pickup button submit the same CSRF-protected form.
  const targets = () => [...plaza.querySelectorAll('[data-pickup-target]')];
  function canDrop(target) {
    const field = draggedForm?.elements.namedItem('vehicle_id');
    return field && (field.tagName === 'SELECT'
      ? [...field.options].some(option => option.value === target.dataset.pickupTarget && !option.disabled)
      : field.value === target.dataset.pickupTarget);
  }
  liveScene.addEventListener('dragstart', event => {
    const person = event.target.closest('[data-pickup-form]');
    if (!person) return;
    draggedForm = document.getElementById(person.dataset.pickupForm);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', person.dataset.pickupForm);
    targets().forEach(target => target.classList.toggle('pickup-ready', Boolean(canDrop(target))));
  });
  liveScene.addEventListener('dragend', () => {
    draggedForm = null;
    pointerDown = false;
    targets().forEach(target => target.classList.remove('pickup-ready'));
    applyPending();
  });
  liveScene.addEventListener('dragover', event => {
    const target = event.target.closest('[data-pickup-target]');
    if (!target || !canDrop(target)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  });
  liveScene.addEventListener('drop', event => {
    const target = event.target.closest('[data-pickup-target]');
    if (!target || !canDrop(target)) return;
    event.preventDefault();
    const form = draggedForm;
    form.elements.namedItem('vehicle_id').value = target.dataset.pickupTarget;
    draggedForm = null;
    targets().forEach(item => item.classList.remove('pickup-ready'));
    form.requestSubmit();
  });

  function hasDraft() {
    return [...liveScene.querySelectorAll('select, textarea, input:not([type=hidden]):not([readonly])')].some(field => {
      if (field.tagName === 'SELECT') {
        const initial = [...field.options].find(option => option.defaultSelected) || field.options[0];
        return field.value !== (initial?.value || '');
      }
      if (field.type === 'checkbox' || field.type === 'radio') return field.checked !== field.defaultChecked;
      return field.value !== field.defaultValue;
    });
  }
  function busy() {
    const active = document.activeElement;
    return submitting || pointerDown || draggedForm || hasDraft() || performance.now() - lastScroll < 250
      || (liveScene.contains(active) && active.matches('input, select, textarea, [contenteditable=true]'))
      || window.getSelection()?.isCollapsed === false;
  }
  function key(node) {
    return node.nodeType === Node.ELEMENT_NODE
      ? node.dataset.syncKey || node.id || node.dataset.select || node.dataset.detail || '' : '';
  }
  function compatible(a, b) {
    return a.nodeType === b.nodeType && a.nodeName === b.nodeName;
  }
  function patch(current, incoming) {
    if (current.isEqualNode(incoming) || current.nodeType === Node.ELEMENT_NODE && current.hasAttribute('data-local')) return;
    if (current.nodeType !== Node.ELEMENT_NODE) {
      current.nodeValue = incoming.nodeValue;
      return;
    }
    for (const attr of [...current.attributes]) {
      if (!incoming.hasAttribute(attr.name)) current.removeAttribute(attr.name);
    }
    for (const attr of incoming.attributes) {
      if (current.getAttribute(attr.name) !== attr.value) current.setAttribute(attr.name, attr.value);
    }
    let cursor = current.firstChild;
    for (const wanted of incoming.childNodes) {
      const wantedKey = key(wanted);
      let match = wantedKey
        ? [...current.childNodes].find(node => key(node) === wantedKey && compatible(node, wanted))
        : cursor && !key(cursor) && compatible(cursor, wanted) ? cursor : null;
      if (!match) {
        match = wanted.cloneNode(true);
        current.insertBefore(match, cursor);
      } else {
        if (match !== cursor) current.insertBefore(match, cursor);
        patch(match, wanted);
      }
      cursor = match.nextSibling;
    }
    while (cursor) {
      const next = cursor.nextSibling;
      cursor.remove();
      cursor = next;
    }
  }
  function applyPending(force = false) {
    if (!pending || stopped || submitting) return;
    if (!force && busy()) {
      status.textContent = '有新安排，当前操作完成后同步';
      syncNow.hidden = !hasDraft();
      return;
    }
    const incoming = new DOMParser().parseFromString(pending.html, 'text/html').querySelector('[data-live-scene]');
    if (!incoming) {
      pending = null;
      status.textContent = '同步暂时中断，正在自动重试';
      return;
    }
    if (![...incoming.querySelectorAll('[data-detail]')].some(panel => panel.dataset.detail === selected)) {
      selected = incoming.querySelector('[data-plaza]').dataset.focus;
    }
    select(incoming, selected);
    const x = window.scrollX;
    const y = window.scrollY;
    patch(liveScene, incoming);
    const url = new URL(window.location.href);
    url.searchParams.set('focus', selected);
    window.history.replaceState(null, '', url);
    window.scrollTo(x, y);
    pending = null;
    syncNow.hidden = true;
    status.textContent = '已同步最新安排';
  }
  liveScene.addEventListener('submit', () => { submitting = true; });
  liveScene.addEventListener('pointerdown', () => { pointerDown = true; });
  window.addEventListener('pointerup', () => { pointerDown = false; setTimeout(() => applyPending(), 0); });
  window.addEventListener('pointercancel', () => { pointerDown = false; });
  window.addEventListener('blur', () => { pointerDown = false; });
  window.addEventListener('scroll', () => { lastScroll = performance.now(); }, { passive: true });
  window.addEventListener('pageshow', () => { submitting = false; });
  liveScene.addEventListener('focusout', () => setTimeout(() => applyPending(), 0));
  syncNow.addEventListener('click', () => {
    // This explicit action discards only the unsubmitted choices in the scene.
    liveScene.querySelectorAll('form').forEach(form => form.reset());
    applyPending(true);
  });

  async function poll() {
    if (stopped) return;
    let controller;
    let timeout;
    try {
      if (document.hidden || submitting) return;
      const url = new URL(liveScene.dataset.syncUrl, window.location.origin);
      url.searchParams.set('revision', liveScene.dataset.revision);
      url.searchParams.set('viewer', liveScene.dataset.viewer);
      url.searchParams.set('focus', selected);
      controller = new AbortController();
      timeout = setTimeout(() => controller.abort(), 10000);
      const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', signal: controller.signal });
      if ([401, 403, 404, 409].includes(response.status) || response.redirected) {
        stopped = true;
        pending = null;
        syncNow.hidden = true;
        reload.hidden = false;
        status.textContent = '登录状态或活动已变化，请重新加载页面';
        return;
      }
      if (!response.ok) throw new Error('Sync unavailable');
      const update = await response.json();
      if (update.html) pending = update;
      if (pending) applyPending();
      else status.textContent = '自动同步中 · 每 3 秒检查';
    } catch {
      status.textContent = '同步暂时中断，正在自动重试';
    } finally {
      clearTimeout(timeout);
      if (!stopped) setTimeout(poll, 3000);
    }
  }
  setTimeout(poll, 3000);
}

document.querySelectorAll('[data-travel-form]').forEach(form => {
  const mode = form.querySelector('[name=mode]');
  const vehicleConfirm = document.querySelector('[data-vehicle-confirm]');
  const vehicleAgree = vehicleConfirm.querySelector('[data-vehicle-agree]');
  const vehicleConsent = form.querySelector('[data-vehicle-consent]');
  let vehicleAccepted = false;
  let previousAppearance = form.querySelector('[name=appearance]:checked')?.value;
  if (!previousAppearance || previousAppearance === 'v800') previousAppearance = form.dataset.defaultAppearance;
  function confirmVehicleSelection() {
    const appearance = form.querySelector('[name=appearance]:checked')?.value;
    if (appearance && appearance !== 'v800') previousAppearance = appearance;
    if (mode.value === 'drive' && appearance === 'v800' && !vehicleAccepted && !vehicleConfirm.open) {
      vehicleConfirm.returnValue = '';
      vehicleConfirm.showModal();
    }
  }
  vehicleConfirm.querySelector('[data-vehicle-cancel]').addEventListener('click', () => vehicleConfirm.close('cancel'));
  vehicleAgree.addEventListener('click', () => {
    vehicleAccepted = true;
    vehicleConsent.disabled = false;
    vehicleConfirm.close('agree');
  });
  vehicleConfirm.addEventListener('close', () => {
    if (vehicleConfirm.returnValue !== 'agree') {
      form.querySelector(`[name=appearance][value="${previousAppearance}"]`).checked = true;
      updateColors();
    }
  });
  // Back/forward cache restores the page's JS state; a new visit must ask again.
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      vehicleAccepted = false;
      vehicleConsent.disabled = true;
      confirmVehicleSelection();
    }
  });
  function updateColors() {
    const appearance = form.querySelector('[name=appearance]:checked')?.value;
    form.querySelectorAll('[data-color-picker]').forEach(group => {
      const enabled = mode.value === 'drive' && appearance === group.dataset.colorPicker;
      group.hidden = !enabled;
      group.querySelectorAll('input').forEach(input => {
        input.disabled = !enabled;
        input.required = enabled;
      });
      const selected = group.querySelector('input:checked');
      if (selected) {
        form.querySelectorAll(`[data-vehicle-preview="${group.dataset.colorPicker}"]`).forEach(preview => {
          preview.src = selected.dataset.colorImage;
        });
      }
    });
  }
  function updateFields() {
    form.querySelectorAll('[data-mode-fields]').forEach(group => {
      const enabled = group.dataset.modeFields.split(' ').includes(mode.value);
      group.hidden = !enabled;
      group.querySelectorAll('input, select, textarea').forEach(input => {
        input.disabled = !enabled;
        if (input.hasAttribute('data-mode-required')) input.required = enabled;
      });
    });
    updateColors();
    const note = form.querySelector('[data-note]');
    note.hidden = mode.value === 'pending';
    note.querySelector('textarea').disabled = note.hidden;
    const confirm = form.querySelector('[data-driver-confirm]');
    if (confirm) {
      confirm.hidden = mode.value === 'drive';
      const checkbox = confirm.querySelector('input');
      checkbox.disabled = confirm.hidden;
      checkbox.required = !confirm.hidden;
    }
    confirmVehicleSelection();
  }
  mode.addEventListener('change', updateFields);
  form.querySelectorAll('[name=appearance], [data-color-image]').forEach(input => {
    input.addEventListener('change', () => {
      updateColors();
      confirmVehicleSelection();
    });
  });
  updateFields();
});

document.addEventListener('click', async event => {
  if (!event.target.closest('[data-share]')) return;
  const input = document.getElementById('share-url');
  const box = document.getElementById('share-box');
  input.value = window.location.origin + window.location.pathname;
  box.hidden = false;
  input.focus();
  input.select();
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(input.value);
      box.querySelector('small').textContent = '链接已复制，可以发到部门群。';
    }
  } catch {
    // Plain HTTP LAN deployments still support selecting and manually copying the URL.
    box.querySelector('small').textContent = '请选择并复制链接，发给参加活动的同事。';
  }
});

document.querySelector('[data-back]')?.addEventListener('click', () => {
  if (window.history.length > 1) window.history.back();
  else window.location.href = '/events';
});
