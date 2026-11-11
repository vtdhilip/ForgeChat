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
const TOKEN = __ENV.TOKEN || '';

const authHeaders = {
  'Content-Type': 'application/json',
  'Cookie': `synapticchat_token=${TOKEN}; forgecrm_token=${TOKEN}`,
};

export default function () {
  // ── 1. Authentication & Session ──
  group('1. Authentication & Session', () => {
    // Auth status (Checks if setup is needed)
    let res = http.get(`${BASE_URL}/api/auth/status`);
    check(res, {
      'GET /api/auth/status is 200': (r) => r.status === 200,
      'Instance is initialized': (r) => JSON.parse(r.body).setupRequired === false,
    });

    // Auth me (Session validation & user profile)
    res = http.get(`${BASE_URL}/api/auth/me`, { headers: authHeaders });
    check(res, {
      'GET /api/auth/me is 200': (r) => r.status === 200,
      'User is admin': (r) => JSON.parse(r.body).user.role === 'admin',
      'User has organizations': (r) => Array.isArray(JSON.parse(r.body).user.organizations),
    });
  });

  // ── 2. Organizations & Tenancy Switching ──
  group('2. Organizations & Tenancy', () => {
    // List organizations
    let res = http.get(`${BASE_URL}/api/organizations`, { headers: authHeaders });
    check(res, {
      'GET /api/organizations is 200': (r) => r.status === 200,
      'Has organization list': (r) => Array.isArray(JSON.parse(r.body).organizations),
    });

    // Super Admin Overview
    res = http.get(`${BASE_URL}/api/organizations/super-admin/overview`, { headers: authHeaders });
    check(res, {
      'GET /api/organizations/super-admin/overview is 200': (r) => r.status === 200,
      'Overview contains stats': (r) => JSON.parse(r.body).stats !== undefined,
    });

    // Switch Organization (Button: Switch Org)
    const orgId = '26e7b672-5558-4a4b-9aed-926c6b71d995';
    res = http.post(`${BASE_URL}/api/organizations/switch`, JSON.stringify({ org_id: orgId }), { headers: authHeaders });
    check(res, {
      'POST /api/organizations/switch is 200': (r) => r.status === 200,
      'Active org switched': (r) => JSON.parse(r.body).activeOrg && JSON.parse(r.body).activeOrg.id === orgId,
    });

    // Update Modules Config (Button: Module Toggles)
    res = http.put(
      `${BASE_URL}/api/organizations/${orgId}/modules`,
      JSON.stringify({ modules: { chats: true, media: true, contacts: true }, plan: 'starter' }),
      { headers: authHeaders }
    );
    check(res, {
      'PUT /api/organizations/:id/modules is 200': (r) => r.status === 200,
      'Update modules success': (r) => JSON.parse(r.body).success === true,
    });
  });

  // ── 3. Dashboard Analytics ──
  group('3. Dashboard Analytics', () => {
    const ranges = ['7d', '30d', '90d'];
    for (const r of ranges) {
      const res = http.get(`${BASE_URL}/api/dashboard?range=${r}`, { headers: authHeaders });
      check(res, {
        [`GET /api/dashboard?range=${r} is 200`]: (res) => res.status === 200,
        [`Dashboard has KPIs for ${r}`]: (res) => {
          const body = JSON.parse(res.body);
          return body.kpis !== undefined && body.range === r;
        },
      });
    }
  });

  // ── 4. WhatsApp Accounts & Numbers ──
  group('4. WhatsApp Accounts & Numbers', () => {
    let res = http.get(`${BASE_URL}/api/whatsapp-accounts`, { headers: authHeaders });
    check(res, {
      'GET /api/whatsapp-accounts is 200': (r) => r.status === 200,
      'Accounts list returned': (r) => Array.isArray(JSON.parse(r.body)),
    });

    res = http.get(`${BASE_URL}/api/numbers`, { headers: authHeaders });
    check(res, {
      'GET /api/numbers is 200': (r) => r.status === 200,
      'Numbers list returned': (r) => Array.isArray(JSON.parse(r.body)),
    });
  });

  // ── 5. Contacts & CRM Taxonomy ──
  group('5. Contacts & CRM Taxonomy', () => {
    const waNumber = '918248933981';

    // List contacts for WA number
    let res = http.get(`${BASE_URL}/api/contacts?waNumber=${waNumber}`, { headers: authHeaders });
    check(res, {
      'GET /api/contacts is 200': (r) => r.status === 200,
      'Contacts list returned': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // Saved contacts
    res = http.get(`${BASE_URL}/api/saved-contacts?waNumber=${waNumber}`, { headers: authHeaders });
    check(res, {
      'GET /api/saved-contacts is 200': (r) => r.status === 200,
      'Saved contacts returned': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // Contact Custom Fields CRUD (Button: Add Custom Field)
    res = http.get(`${BASE_URL}/api/contact-fields`, { headers: authHeaders });
    check(res, {
      'GET /api/contact-fields is 200': (r) => r.status === 200,
      'Contact fields is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    const fieldName = `k6_field_${Date.now()}`;
    res = http.post(
      `${BASE_URL}/api/contact-fields`,
      JSON.stringify({ name: fieldName, fieldType: 'text', description: 'K6 Automated Test Field' }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/contact-fields is 200/201': (r) => r.status === 200 || r.status === 201,
    });
    const fieldId = res.status === 200 || res.status === 201 ? JSON.parse(res.body).id : null;
    if (fieldId) {
      const delField = http.del(`${BASE_URL}/api/contact-fields/${fieldId}`, null, { headers: authHeaders });
      check(delField, { 'DELETE /api/contact-fields/:id is 200': (r) => r.status === 200 });
    }

    // Categories CRUD (Button: Add Category)
    res = http.get(`${BASE_URL}/api/categories`, { headers: authHeaders });
    check(res, {
      'GET /api/categories is 200': (r) => r.status === 200,
      'Categories is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    res = http.post(
      `${BASE_URL}/api/categories`,
      JSON.stringify({ name: `K6 Category ${Date.now()}` }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/categories is 200/201': (r) => r.status === 200 || r.status === 201,
    });
    const catId = res.status === 200 || res.status === 201 ? JSON.parse(res.body).id : null;

    // Tags CRUD under Category (Button: Add Tag)
    if (catId) {
      res = http.get(`${BASE_URL}/api/tags`, { headers: authHeaders });
      check(res, {
        'GET /api/tags is 200': (r) => r.status === 200,
        'Tags is array': (r) => Array.isArray(JSON.parse(r.body)),
      });

      const tagRes = http.post(
        `${BASE_URL}/api/tags`,
        JSON.stringify({ name: `k6-tag-${Date.now()}`, color: '#25D366', categoryId: String(catId) }),
        { headers: authHeaders }
      );
      check(tagRes, {
        'POST /api/tags is 200/201': (r) => r.status === 200 || r.status === 201,
      });
      const tagId = tagRes.status === 200 || tagRes.status === 201 ? JSON.parse(tagRes.body).id : null;
      if (tagId) {
        const delTag = http.del(`${BASE_URL}/api/tags/${tagId}`, null, { headers: authHeaders });
        check(delTag, { 'DELETE /api/tags/:id is 200': (r) => r.status === 200 });
      }

      // Cleanup category
      const delCat = http.del(`${BASE_URL}/api/categories/${catId}`, null, { headers: authHeaders });
      check(delCat, { 'DELETE /api/categories/:id is 200': (r) => r.status === 200 });
    }

    // Save Contact Profile (Button: Save Contact Profile)
    const testContactNumber = `9199999${Math.floor(10000 + Math.random() * 90000)}`;
    res = http.post(
      `${BASE_URL}/api/contacts/save`,
      JSON.stringify({
        waNumber: waNumber,
        contactNumber: testContactNumber,
        name: 'K6 Automated Tester',
        tags: ['k6-verified'],
      }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/contacts/save is 200': (r) => r.status === 200,
      'Contact saved': (r) => JSON.parse(r.body).ok === true,
    });

    // Clean up created contact
    const delContact = http.del(
      `${BASE_URL}/api/contact?waNumber=${waNumber}&contactNumber=${testContactNumber}`,
      null,
      { headers: authHeaders }
    );
    check(delContact, {
      'DELETE /api/contact is 200': (r) => r.status === 200,
    });
  });

  // ── 6. Pipelines & Sales Kanban ──
  group('6. Pipelines & Deals', () => {
    let res = http.get(`${BASE_URL}/api/pipelines`, { headers: authHeaders });
    check(res, {
      'GET /api/pipelines is 200': (r) => r.status === 200,
      'Pipelines is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // Pipeline CRUD (Button: Create Pipeline)
    res = http.post(
      `${BASE_URL}/api/pipelines`,
      JSON.stringify({ name: `K6 Sales Pipeline ${Date.now()}` }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/pipelines is 200/201': (r) => r.status === 200 || r.status === 201,
    });
    const pipelineId = res.status === 200 || res.status === 201 ? JSON.parse(res.body).id : null;

    if (pipelineId) {
      // Add stage to pipeline (Button: Add Stage)
      const stageRes = http.post(
        `${BASE_URL}/api/pipelines/${pipelineId}/stages`,
        JSON.stringify({ name: 'Qualified Lead', stage_order: 1 }),
        { headers: authHeaders }
      );
      check(stageRes, {
        'POST /api/pipelines/:id/stages is 200/201': (r) => r.status === 200 || r.status === 201,
      });
      const stageId = stageRes.status === 200 || stageRes.status === 201 ? JSON.parse(stageRes.body).id : null;

      // Create Deal (Button: Add Deal)
      const dealRes = http.post(
        `${BASE_URL}/api/deals`,
        JSON.stringify({
          pipelineId: pipelineId,
          stageId: stageId,
          title: 'K6 Enterprise Deal',
          value: 150000.0,
          currency: 'INR',
        }),
        { headers: authHeaders }
      );
      check(dealRes, {
        'POST /api/deals is 200/201': (r) => r.status === 200 || r.status === 201,
      });
      const dealId = dealRes.status === 200 || dealRes.status === 201 ? JSON.parse(dealRes.body).id : null;

      // Query Deals & Metrics for pipeline
      const dealsList = http.get(`${BASE_URL}/api/deals?pipelineId=${pipelineId}`, { headers: authHeaders });
      check(dealsList, {
        'GET /api/deals?pipelineId is 200': (r) => r.status === 200,
        'Deals is array': (r) => Array.isArray(JSON.parse(r.body)),
      });

      const metricsRes = http.get(`${BASE_URL}/api/deals/metrics?pipelineId=${pipelineId}`, { headers: authHeaders });
      check(metricsRes, {
        'GET /api/deals/metrics?pipelineId is 200': (r) => r.status === 200,
      });

      // Cleanup deal
      if (dealId) {
        http.del(`${BASE_URL}/api/deals/${dealId}`, null, { headers: authHeaders });
      }

      // Cleanup test pipeline
      const delPipe = http.del(`${BASE_URL}/api/pipelines/${pipelineId}`, null, { headers: authHeaders });
      check(delPipe, { 'DELETE /api/pipelines/:id is 200': (r) => r.status === 200 });
    }
  });

  // ── 7. Templates & Broadcasts ──
  group('7. Templates & Broadcasts', () => {
    // List WhatsApp templates
    let res = http.get(`${BASE_URL}/api/templates`, { headers: authHeaders });
    check(res, {
      'GET /api/templates is 200': (r) => r.status === 200,
      'Templates is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // List broadcasts
    res = http.get(`${BASE_URL}/api/broadcasts`, { headers: authHeaders });
    check(res, {
      'GET /api/broadcasts is 200': (r) => r.status === 200,
      'Broadcasts is array': (r) => Array.isArray(JSON.parse(r.body)),
    });
  });

  // ── 8. AI Agents & AI Models ──
  group('8. AI Agents & Models', () => {
    // List AI models
    let res = http.get(`${BASE_URL}/api/ai-models`, { headers: authHeaders });
    check(res, {
      'GET /api/ai-models is 200': (r) => r.status === 200,
      'Models is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // List AI agents
    res = http.get(`${BASE_URL}/api/agents`, { headers: authHeaders });
    check(res, {
      'GET /api/agents is 200': (r) => r.status === 200,
      'Agents is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // AI Agent CRUD (Button: Create Agent)
    res = http.post(
      `${BASE_URL}/api/agents`,
      JSON.stringify({
        name: `K6 Assistant ${Date.now()}`,
        systemPrompt: 'You are an automated support agent verified by k6 test suite.',
        status: 'draft',
      }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/agents is 200/201': (r) => r.status === 200 || r.status === 201,
    });
    const agentId = res.status === 200 || res.status === 201 ? JSON.parse(res.body).id : null;

    if (agentId) {
      const delAgent = http.del(`${BASE_URL}/api/agents/${agentId}`, null, { headers: authHeaders });
      check(delAgent, { 'DELETE /api/agents/:id is 200': (r) => r.status === 200 });
    }
  });

  // ── 9. Chatbots & Automations ──
  group('9. Chatbots & Automations', () => {
    let res = http.get(`${BASE_URL}/api/chatbots`, { headers: authHeaders });
    check(res, {
      'GET /api/chatbots is 200': (r) => r.status === 200,
      'Chatbots is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // Create Chatbot Flow (Button: Create Automation)
    res = http.post(
      `${BASE_URL}/api/chatbots`,
      JSON.stringify({
        name: `K6 Automation ${Date.now()}`,
        trigger_type: 'keyword',
        trigger_keyword: 'k6start',
        nodes: [{ id: '1', type: 'trigger', data: { label: 'Start' } }],
        edges: [],
      }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/chatbots is 200/201': (r) => r.status === 200 || r.status === 201,
    });
    const botId = res.status === 200 || res.status === 201 ? JSON.parse(res.body).id : null;

    if (botId) {
      const delBot = http.del(`${BASE_URL}/api/chatbots/${botId}`, null, { headers: authHeaders });
      check(delBot, { 'DELETE /api/chatbots/:id is 200': (r) => r.status === 200 });
    }
  });

  // ── 10. Media Library ──
  group('10. Media Library', () => {
    let res = http.get(`${BASE_URL}/api/media-library`, { headers: authHeaders });
    check(res, {
      'GET /api/media-library is 200': (r) => r.status === 200,
      'Media library list returned': (r) => JSON.parse(r.body).media !== undefined,
    });
  });

  // ── 11. Users Management ──
  group('11. Users Management', () => {
    let res = http.get(`${BASE_URL}/api/users`, { headers: authHeaders });
    check(res, {
      'GET /api/users is 200': (r) => r.status === 200,
      'Users is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    res = http.get(`${BASE_URL}/api/users/1`, { headers: authHeaders });
    check(res, {
      'GET /api/users/1 is 200': (r) => r.status === 200,
      'User 1 is Admin': (r) => JSON.parse(r.body).username === 'admin',
    });
  });

  // ── 12. Model Context Protocol (MCP) Tools ──
  group('12. Model Context Protocol (MCP)', () => {
    let res = http.get(`${BASE_URL}/api/mcp/settings`, { headers: authHeaders });
    check(res, {
      'GET /api/mcp/settings is 200': (r) => r.status === 200,
      'Has MCP master toggle': (r) => JSON.parse(r.body).masterEnabled !== undefined,
    });

    res = http.get(`${BASE_URL}/api/mcp/keys`, { headers: authHeaders });
    check(res, {
      'GET /api/mcp/keys is 200': (r) => r.status === 200,
      'MCP keys is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    // Create MCP API Key (Button: Generate Key)
    res = http.post(
      `${BASE_URL}/api/mcp/keys`,
      JSON.stringify({ label: `K6 MCP Key ${Date.now()}` }),
      { headers: authHeaders }
    );
    check(res, {
      'POST /api/mcp/keys is 201': (r) => r.status === 201 || r.status === 200,
      'Key has plain token': (r) => JSON.parse(r.body).key !== undefined,
    });
  });

  // ── 13. Google Integrations ──
  group('13. Google Integrations', () => {
    let res = http.get(`${BASE_URL}/api/google-integrations/status`, { headers: authHeaders });
    check(res, {
      'GET /api/google-integrations/status is 200': (r) => r.status === 200,
    });

    res = http.get(`${BASE_URL}/api/google-integrations`, { headers: authHeaders });
    check(res, {
      'GET /api/google-integrations is 200': (r) => r.status === 200,
      'Integrations is array': (r) => Array.isArray(JSON.parse(r.body)),
    });
  });

  // ── 14. Webhooks & External Triggers ──
  group('14. Webhooks & Verification', () => {
    // Meta Hub Verification Challenge
    const challenge = 'k6_challenge_verify_token_test';
    let res = http.get(
      `${BASE_URL}/api/webhook?hub.mode=subscribe&hub.challenge=${challenge}&hub.verify_token=synapticchat_verify_token`
    );
    check(res, {
      'GET /api/webhook verification is 200': (r) => r.status === 200,
      'Meta Challenge echoed': (r) => r.body === challenge,
    });
  });
}
