/**
 * API client — fetch wrapper for all backend calls.
 * When stubs are wired to real agents, no changes needed here.
 */
const API = {
  option: 'a',

  async get(path) {
    const sep = path.includes('?') ? '&' : '?';
    const url = path.startsWith('/api') ? path : `/api${path}`;
    const res = await fetch(`${url}${sep}option=${this.option}`);
    return res.json();
  },

  async post(path, body = {}) {
    const sep = path.includes('?') ? '&' : '?';
    const url = path.startsWith('/api') ? path : `/api${path}`;
    const res = await fetch(`${url}${sep}option=${this.option}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  setOption(opt) {
    this.option = opt;
  },
};
