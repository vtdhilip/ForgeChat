const pool = require('../db');
const { enqueueSend } = require('../queue/sendQueue');

/**
 * Extracts variable placeholders {{1}}, {{2}}... from template text
 */
function extractVars(text) {
  const m = [...(text || '').matchAll(/\{\{(\d+)\}\}/g)];
  return [...new Set(m.map(x => parseInt(x[1], 10)))].sort((a, b) => a - b);
}

/**
 * Finds an approved template for order notifications
 */
async function findApprovedTemplate(accountId, preferredNames = [], keywords = []) {
  try {
    const loweredNames = preferredNames.map(n => String(n).trim().toLowerCase());
    // 1. Try preferred exact names (from .env or standard names)
    if (loweredNames.length > 0) {
      const { rows } = await pool.query(
        `SELECT * FROM coexistence.message_templates
          WHERE status ILIKE 'APPROVED'
            AND (whatsapp_account_id = $1 OR whatsapp_account_id IS NULL)
            AND LOWER(name) = ANY($2::text[])
          ORDER BY (CASE WHEN whatsapp_account_id = $1 THEN 0 ELSE 1 END) ASC
          LIMIT 1`,
        [accountId, loweredNames]
      );
      if (rows.length > 0) return rows[0];
    }

    // 2. Try keyword search among approved templates
    for (const kw of keywords) {
      const { rows } = await pool.query(
        `SELECT * FROM coexistence.message_templates
          WHERE status ILIKE 'APPROVED'
            AND (whatsapp_account_id = $1 OR whatsapp_account_id IS NULL)
            AND name ILIKE $2
          ORDER BY (CASE WHEN whatsapp_account_id = $1 THEN 0 ELSE 1 END) ASC
          LIMIT 1`,
        [accountId, `%${kw}%`]
      );
      if (rows.length > 0) return rows[0];
    }
  } catch (err) {
    console.error('[orderNotifications] Error querying templates:', err.message);
  }
  return null;
}

/**
 * Send order shipping / in-transit / out-for-delivery notification
 */
async function sendShippingNotification({
  accountId,
  targetPhone,
  targetName = 'Customer',
  orderNumber = '',
  courier = '',
  awb = '',
  trackingUrl = '',
  status = 'Shipped',
}) {
  const cleanTo = String(targetPhone).replace(/\D/g, '');
  if (!cleanTo || !accountId) return false;

  const envTpl = process.env.WHATSAPP_ORDER_SHIPPED_TEMPLATE || process.env.WHATSAPP_SHIPPING_TEMPLATE;
  const preferred = [
    ...(envTpl ? [envTpl.trim().toLowerCase()] : []),
    'order_shipped',
    'shipping_update',
    'order_tracking',
    'order_status',
    'order_update',
  ];

  const template = await findApprovedTemplate(accountId, preferred, ['ship', 'track', 'order']);
  const localId = `sr-notify-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

  if (template) {
    // Template found — format parameters according to template variables
    const vars = extractVars(template.body);
    const varCount = vars.length > 0 ? Math.max(...vars) : 0;

    // Available variable candidates in order:
    // {{1}} = Customer Name
    // {{2}} = Order Number
    // {{3}} = Courier Name
    // {{4}} = Tracking Link or AWB
    const candidates = [
      targetName,
      orderNumber || 'Order',
      courier || 'Express Courier',
      trackingUrl || (awb ? `AWB: ${awb}` : 'Live Tracking'),
    ];

    const bodyParams = [];
    for (let i = 0; i < varCount; i++) {
      bodyParams.push({
        type: 'text',
        text: String(candidates[i] || ' ').slice(0, 1024),
      });
    }

    const components = [];
    if (bodyParams.length > 0) {
      components.push({ type: 'body', parameters: bodyParams });
    }

    // Dynamic button URL support (e.g. tracking link or AWB)
    const buttons = Array.isArray(template.buttons) ? template.buttons : [];
    buttons.forEach((btn, idx) => {
      if (btn.type === 'URL' && /\{\{\d+\}\}/.test(btn.value || '')) {
        components.push({
          type: 'button',
          sub_type: 'url',
          index: String(idx),
          parameters: [{ type: 'text', text: awb || orderNumber || 'track' }],
        });
      }
    });

    const renderedBody = template.body
      ? template.body.replace(/\{\{(\d+)\}\}/g, (_, n) => candidates[parseInt(n, 10) - 1] || '')
      : `Template: ${template.name}`;

    await pool.query(
      `INSERT INTO coexistence.chat_history
         (message_id, phone_number_id, wa_number, contact_number, to_number,
          direction, message_type, message_body, status, timestamp)
       SELECT $1, phone_number_id, wa_number, $2, $2,
              'outgoing', 'template', $3, 'queued', NOW()
         FROM coexistence.whatsapp_accounts WHERE id = $4`,
      [localId, cleanTo, renderedBody, accountId]
    ).catch(() => {});

    await enqueueSend({
      kind: 'template',
      accountId,
      to: cleanTo,
      localMessageId: localId,
      payload: {
        name: template.name,
        languageCode: template.language || 'en',
        components,
      },
    });

    console.log(`[orderNotifications] ✅ Sent shipping template "${template.name}" to ${cleanTo} for Order ${orderNumber}`);
    return true;
  }

  // Fallback to text message if no approved template is available
  const messageText =
    `🚚 *Your Order #${orderNumber} Has Been Shipped!*\n\n` +
    `Hi ${targetName}, great news! Your package is on its way.\n\n` +
    (courier ? `📦 *Courier:* ${courier}\n` : '') +
    (awb ? `🔖 *Tracking / AWB:* ${awb}\n` : '') +
    (trackingUrl ? `🔗 *Live Tracking Link:*\n👉 ${trackingUrl}\n\n` : '\n') +
    `Thank you for shopping with LINNDEN! 🙏`;

  await pool.query(
    `INSERT INTO coexistence.chat_history
       (message_id, phone_number_id, wa_number, contact_number, to_number,
        direction, message_type, message_body, status, timestamp)
     SELECT $1, phone_number_id, wa_number, $2, $2,
            'outgoing', 'text', $3, 'queued', NOW()
       FROM coexistence.whatsapp_accounts WHERE id = $4`,
    [localId, cleanTo, messageText, accountId]
  ).catch(() => {});

  await enqueueSend({
    kind: 'text',
    accountId,
    to: cleanTo,
    localMessageId: localId,
    payload: { body: messageText, previewUrl: true },
  });

  console.log(`[orderNotifications] ⚠️ Sent text message (no approved template found) to ${cleanTo} for Order ${orderNumber}. Create a Utility template "order_shipped" in Template Builder for delivery outside 24h.`);
  return true;
}

/**
 * Send order delivered confirmation notification
 */
async function sendDeliveryNotification({
  accountId,
  targetPhone,
  targetName = 'Customer',
  orderNumber = '',
}) {
  const cleanTo = String(targetPhone).replace(/\D/g, '');
  if (!cleanTo || !accountId) return false;

  const envTpl = process.env.WHATSAPP_ORDER_DELIVERED_TEMPLATE || process.env.WHATSAPP_DELIVERY_TEMPLATE;
  const preferred = [
    ...(envTpl ? [envTpl.trim().toLowerCase()] : []),
    'order_delivered',
    'delivery_confirmation',
    'order_update',
  ];

  const template = await findApprovedTemplate(accountId, preferred, ['deliver']);
  const localId = `sr-deliver-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

  if (template) {
    const vars = extractVars(template.body);
    const varCount = vars.length > 0 ? Math.max(...vars) : 0;
    const candidates = [targetName, orderNumber || 'Order'];

    const bodyParams = [];
    for (let i = 0; i < varCount; i++) {
      bodyParams.push({
        type: 'text',
        text: String(candidates[i] || ' ').slice(0, 1024),
      });
    }

    const components = bodyParams.length > 0 ? [{ type: 'body', parameters: bodyParams }] : [];
    const renderedBody = template.body
      ? template.body.replace(/\{\{(\d+)\}\}/g, (_, n) => candidates[parseInt(n, 10) - 1] || '')
      : `Template: ${template.name}`;

    await pool.query(
      `INSERT INTO coexistence.chat_history
         (message_id, phone_number_id, wa_number, contact_number, to_number,
          direction, message_type, message_body, status, timestamp)
       SELECT $1, phone_number_id, wa_number, $2, $2,
              'outgoing', 'template', $3, 'queued', NOW()
         FROM coexistence.whatsapp_accounts WHERE id = $4`,
      [localId, cleanTo, renderedBody, accountId]
    ).catch(() => {});

    await enqueueSend({
      kind: 'template',
      accountId,
      to: cleanTo,
      localMessageId: localId,
      payload: {
        name: template.name,
        languageCode: template.language || 'en',
        components,
      },
    });

    console.log(`[orderNotifications] ✅ Sent delivery template "${template.name}" to ${cleanTo} for Order ${orderNumber}`);
    return true;
  }

  const messageText =
    `🎉 *Order Delivered!*\n\n` +
    `Hi ${targetName}, your order *#${orderNumber}* has been successfully delivered.\n\n` +
    `Thank you for shopping with LINNDEN! If you have any feedback, simply reply to this chat. ⭐`;

  await pool.query(
    `INSERT INTO coexistence.chat_history
       (message_id, phone_number_id, wa_number, contact_number, to_number,
        direction, message_type, message_body, status, timestamp)
     SELECT $1, phone_number_id, wa_number, $2, $2,
            'outgoing', 'text', $3, 'queued', NOW()
       FROM coexistence.whatsapp_accounts WHERE id = $4`,
    [localId, cleanTo, messageText, accountId]
  ).catch(() => {});

  await enqueueSend({
    kind: 'text',
    accountId,
    to: cleanTo,
    localMessageId: localId,
    payload: { body: messageText, previewUrl: true },
  });

  console.log(`[orderNotifications] ⚠️ Sent text message (no approved template found) to ${cleanTo} for Order ${orderNumber}. Create a Utility template "order_delivered" in Template Builder.`);
  return true;
}

module.exports = {
  sendShippingNotification,
  sendDeliveryNotification,
  findApprovedTemplate,
};
