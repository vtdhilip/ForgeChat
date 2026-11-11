import http from 'k6/http';
import { check, group } from 'k6';

export const options = {
  scenarios: {
    // 1. Pages & static asset rendering
    pages_test: {
      executor: 'shared-iterations',
      vus: 2,
      iterations: 4,
      maxDuration: '30s',
      exec: 'testPages',
    },
    // 2. Functional business logic & buttons
    functions_test: {
      executor: 'shared-iterations',
      vus: 2,
      iterations: 4,
      maxDuration: '30s',
      exec: 'testFunctions',
    },
  },
  thresholds: {
    checks: ['rate>0.99'],
    http_req_duration: ['p(95)<300'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const TOKEN = __ENV.TOKEN || '';

const authHeaders = {
  'Content-Type': 'application/json',
  'Cookie': `synapticchat_token=${TOKEN}; forgecrm_token=${TOKEN}`,
};

export function testPages() {
  group('Frontend Shell & Static Assets', () => {
    let res = http.get(`${BASE_URL}/`);
    check(res, {
      'Root / returns 200': (r) => r.status === 200,
      'Contains Synaptic Chat title': (r) => r.body.includes('Synaptic Chat'),
    });

    res = http.get(`${BASE_URL}/synaptic-logo.svg`);
    check(res, { 'Logo SVG is 200': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/synaptic-icon.svg`);
    check(res, { 'Icon SVG is 200': (r) => r.status === 200 });
  });

  group('SPA Client Page Navigation', () => {
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
        [`Page /#/${page} serves 200`]: (r) => r.status === 200,
      });
    }
  });
}

export function testFunctions() {
  const orgId = '26e7b672-5558-4a4b-9aed-926c6b71d995';
  const waNumber = '918248933981';

  group('Auth & Organization Switcher', () => {
    let res = http.get(`${BASE_URL}/api/auth/me`, { headers: authHeaders });
    check(res, {
      'Auth /me returns active admin': (r) => r.status === 200 && JSON.parse(r.body).user.role === 'admin',
    });

    res = http.post(`${BASE_URL}/api/organizations/switch`, JSON.stringify({ org_id: orgId }), { headers: authHeaders });
    check(res, {
      'Switch Org button works': (r) => r.status === 200 && JSON.parse(r.body).activeOrg.id === orgId,
    });

    res = http.put(
      `${BASE_URL}/api/organizations/${orgId}/modules`,
      JSON.stringify({ modules: { chats: true, contacts: true }, plan: 'starter' }),
      { headers: authHeaders }
    );
    check(res, {
      'Update Modules toggle works': (r) => r.status === 200 && JSON.parse(r.body).success === true,
    });
  });

  group('Dashboard KPI Ranges', () => {
    for (const r of ['7d', '30d', '90d']) {
      const res = http.get(`${BASE_URL}/api/dashboard?range=${r}`, { headers: authHeaders });
      check(res, {
        [`Dashboard range ${r} returns valid KPIs`]: (res) => res.status === 200 && JSON.parse(res.body).kpis !== undefined,
      });
    }
  });

  group('WhatsApp, Contacts & CRM Taxonomy', () => {
    let res = http.get(`${BASE_URL}/api/whatsapp-accounts`, { headers: authHeaders });
    check(res, { 'WhatsApp accounts listed': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/numbers`, { headers: authHeaders });
    check(res, { 'WhatsApp active numbers listed': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/contacts?waNumber=${waNumber}`, { headers: authHeaders });
    check(res, { 'Contacts list returned': (r) => r.status === 200 });

    // Custom Field Lifecycle
    const fieldName = `k6_f_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    res = http.post(
      `${BASE_URL}/api/contact-fields`,
      JSON.stringify({ name: fieldName, fieldType: 'text', description: 'K6 Suite' }),
      { headers: authHeaders }
    );
    check(res, { 'Add Custom Field button works': (r) => r.status === 200 || r.status === 201 });
    const fieldId = res.status < 300 ? JSON.parse(res.body).id : null;
    if (fieldId) {
      http.del(`${BASE_URL}/api/contact-fields/${fieldId}`, null, { headers: authHeaders });
    }

    // Category & Tag Lifecycle
    res = http.post(
      `${BASE_URL}/api/categories`,
      JSON.stringify({ name: `Cat_${Date.now()}` }),
      { headers: authHeaders }
    );
    check(res, { 'Add Category button works': (r) => r.status === 200 || r.status === 201 });
    const catId = res.status < 300 ? JSON.parse(res.body).id : null;

    if (catId) {
      const tagRes = http.post(
        `${BASE_URL}/api/tags`,
        JSON.stringify({ name: `tag_${Date.now()}`, color: '#10b981', categoryId: String(catId) }),
        { headers: authHeaders }
      );
      check(tagRes, { 'Add Tag button works': (r) => r.status === 200 || r.status === 201 });
      const tagId = tagRes.status < 300 ? JSON.parse(tagRes.body).id : null;
      if (tagId) http.del(`${BASE_URL}/api/tags/${tagId}`, null, { headers: authHeaders });
      http.del(`${BASE_URL}/api/categories/${catId}`, null, { headers: authHeaders });
    }

    // Save Contact
    const testNum = `919999${Math.floor(100000 + Math.random() * 900000)}`;
    res = http.post(
      `${BASE_URL}/api/contacts/save`,
      JSON.stringify({ waNumber, contactNumber: testNum, name: 'K6 Suite User', tags: ['k6'] }),
      { headers: authHeaders }
    );
    check(res, { 'Save Contact button works': (r) => r.status === 200 });
    http.del(`${BASE_URL}/api/contact?waNumber=${waNumber}&contactNumber=${testNum}`, null, { headers: authHeaders });
  });

  group('Pipelines, Deals & Kanban', () => {
    // Pipeline Create
    const pipeRes = http.post(
      `${BASE_URL}/api/pipelines`,
      JSON.stringify({ name: `Pipeline_${Date.now()}` }),
      { headers: authHeaders }
    );
    check(pipeRes, { 'Create Pipeline button works': (r) => r.status === 200 || r.status === 201 });
    const pipeId = pipeRes.status < 300 ? JSON.parse(pipeRes.body).id : null;

    if (pipeId) {
      // Stage Create
      const stageRes = http.post(
        `${BASE_URL}/api/pipelines/${pipeId}/stages`,
        JSON.stringify({ name: 'Lead Qualified', stage_order: 1 }),
        { headers: authHeaders }
      );
      check(stageRes, { 'Add Stage button works': (r) => r.status === 200 || r.status === 201 });
      const stageId = stageRes.status < 300 ? JSON.parse(stageRes.body).id : null;

      // Deal Create
      const dealRes = http.post(
        `${BASE_URL}/api/deals`,
        JSON.stringify({
          pipelineId: pipeId,
          stageId: stageId,
          title: 'K6 Enterprise Deal',
          value: 200000,
          currency: 'INR',
        }),
        { headers: authHeaders }
      );
      check(dealRes, { 'Create Deal button works': (r) => r.status === 200 || r.status === 201 });
      const dealId = dealRes.status < 300 ? JSON.parse(dealRes.body).id : null;

      // Query Deals & Metrics
      const dealsList = http.get(`${BASE_URL}/api/deals?pipelineId=${pipeId}`, { headers: authHeaders });
      check(dealsList, { 'Deals listed': (r) => r.status === 200 });

      const metricsRes = http.get(`${BASE_URL}/api/deals/metrics?pipelineId=${pipeId}`, { headers: authHeaders });
      check(metricsRes, { 'Deal Metrics calculated': (r) => r.status === 200 });

      if (dealId) http.del(`${BASE_URL}/api/deals/${dealId}`, null, { headers: authHeaders });
      http.del(`${BASE_URL}/api/pipelines/${pipeId}`, null, { headers: authHeaders });
    }
  });

  group('Templates, Broadcasts & AI Tools', () => {
    let res = http.get(`${BASE_URL}/api/templates`, { headers: authHeaders });
    check(res, { 'Templates catalog accessible': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/broadcasts`, { headers: authHeaders });
    check(res, { 'Broadcasts list accessible': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/ai-models`, { headers: authHeaders });
    check(res, { 'AI Models catalog accessible': (r) => r.status === 200 });

    // AI Agent Creation
    res = http.post(
      `${BASE_URL}/api/agents`,
      JSON.stringify({ name: `Agent_${Date.now()}`, systemPrompt: 'Test Prompt', status: 'draft' }),
      { headers: authHeaders }
    );
    check(res, { 'Create Agent button works': (r) => r.status === 200 || r.status === 201 });
    const agentId = res.status < 300 ? JSON.parse(res.body).id : null;
    if (agentId) http.del(`${BASE_URL}/api/agents/${agentId}`, null, { headers: authHeaders });

    // Chatbot Automation Creation
    res = http.post(
      `${BASE_URL}/api/chatbots`,
      JSON.stringify({
        name: `Bot_${Date.now()}`,
        trigger_type: 'keyword',
        trigger_keyword: 'k6start',
        nodes: [{ id: '1', type: 'trigger', data: { label: 'Start' } }],
        edges: [],
      }),
      { headers: authHeaders }
    );
    check(res, { 'Create Chatbot button works': (r) => r.status === 200 || r.status === 201 });
    const botId = res.status < 300 ? JSON.parse(res.body).id : null;
    if (botId) http.del(`${BASE_URL}/api/chatbots/${botId}`, null, { headers: authHeaders });
  });

  group('Media, Users, MCP & Webhooks', () => {
    let res = http.get(`${BASE_URL}/api/media-library`, { headers: authHeaders });
    check(res, { 'Media library loaded': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/users`, { headers: authHeaders });
    check(res, { 'Users list loaded': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/api/mcp/settings`, { headers: authHeaders });
    check(res, { 'MCP settings loaded': (r) => r.status === 200 });

    // Create MCP Key
    res = http.post(`${BASE_URL}/api/mcp/keys`, JSON.stringify({ label: `Key_${Date.now()}` }), { headers: authHeaders });
    check(res, { 'Generate MCP Key button works': (r) => r.status === 200 || r.status === 201 });

    // Webhook Hub Verification
    const challenge = 'k6_challenge_final';
    res = http.get(`${BASE_URL}/api/webhook?hub.mode=subscribe&hub.challenge=${challenge}&hub.verify_token=synapticchat_verify_token`);
    check(res, { 'Meta Webhook verified': (r) => r.status === 200 && r.body === challenge });
  });
}
