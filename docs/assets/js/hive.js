document.addEventListener('DOMContentLoaded', () => {
  // Install tabs
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(target).classList.add('active');
    });
  });

  // Copy buttons
  document.querySelectorAll('.copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const code = btn.closest('.code-block').querySelector('code').innerText;
      navigator.clipboard.writeText(code).then(() => {
        const old = btn.innerText;
        btn.innerText = 'COPIED';
        setTimeout(() => btn.innerText = old, 1200);
      });
    });
  });

  // Keyboard nav for tabs
  tabs.forEach((tab, idx) => {
    tab.addEventListener('keydown', (e) => {
      let next;
      if (e.key === 'ArrowRight') next = tabs[idx + 1] || tabs[0];
      if (e.key === 'ArrowLeft') next = tabs[idx - 1] || tabs[tabs.length - 1];
      if (next) { next.focus(); next.click(); }
    });
  });
});
