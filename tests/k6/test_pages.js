import http from 'k6/http';
import { check, group } from 'k6';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    checks: ['rate>0.99'],
    http_req_duration: ['p(95)<300'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  group('1. Frontend Static Assets & Shell', () => {
    // Root Document
    let res = http.get(`${BASE_URL}/`);
    check(res, {
      'root / returns 200': (r) => r.status === 200,
      'root / is HTML': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('text/html'),
      'root / contains Synaptic Chat title': (r) => r.body.includes('Synaptic Chat'),
      'root / contains root element': (r) => r.body.includes('id="root"'),
    });

    // Explicit /index.html
    res = http.get(`${BASE_URL}/index.html`);
    check(res, {
      '/index.html returns 200': (r) => r.status === 200,
      '/index.html is HTML': (r) => r.headers['Content-Type'].includes('text/html'),
    });

    // Branding Logos
    res = http.get(`${BASE_URL}/synaptic-logo.svg`);
    check(res, {
      '/synaptic-logo.svg returns 200': (r) => r.status === 200,
      '/synaptic-logo.svg is SVG': (r) => r.headers['Content-Type'].includes('image/svg+xml'),
    });

    res = http.get(`${BASE_URL}/synaptic-icon.svg`);
    check(res, {
      '/synaptic-icon.svg returns 200': (r) => r.status === 200,
      '/synaptic-icon.svg is SVG': (r) => r.headers['Content-Type'].includes('image/svg+xml'),
    });
  });

  group('2. Frontend Client Routes (SPA Deep Links)', () => {
    const pages = [
      'home',
      'chats',
      'contacts',
      'pipelines',
      'bulk-message',
      'template-builder',
      'chatbot-builder',
      'admin-settings',
      'media-library',
      'ai-agent-builder',
      'super-admin',
    ];

    for (const page of pages) {
      const res = http.get(`${BASE_URL}/#/${page}`);
      check(res, {
        [`Page /#/${page} serves SPA HTML (200)`]: (r) => r.status === 200,
        [`Page /#/${page} has HTML content`]: (r) => r.body.includes('id="root"'),
      });
    }
  });
}
