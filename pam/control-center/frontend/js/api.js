/**
 * API client — fetch wrapper for all backend calls.
 * KeeperPAM is the sole target — option is fixed to 'b'.
 */
const API = {
  option: 'b',

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
};
