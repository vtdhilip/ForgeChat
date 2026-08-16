/**
 * Order Status Webhook Handler (Google Sheets / External)
 *
 * Receives order fulfillment & shipping status updates from Google Sheets and:
 *  1. Updates the order in coexistence.orders (status, courier, tracking_number, tracking_url)
 *  2. Sends an automated WhatsApp status notification to the customer (Shipped, Delivered, Processing, Cancelled)
 *
 * Endpoint: POST /api/orders/sheet-status-update
 */

const { Router } = require('express');
const pool = require('../db');
const { enqueueSend } = require('../queue/sendQueue');
const { ensureOrdersTable } = require('../services/checkout');

const router = Router();

// Helper to format clean phone number
function cleanPhone(phone) {
  let p = String(phone || '').replace(/\D/g, '');
  if (p.length === 10) p = '91' + p; // default to India country code if 10 digits
  return p;
}

// ─── Format WhatsApp Message for Status ─────────────────────────────────────
function buildStatusMessage({ status, orderNumber, customerName, courier, trackingNumber, trackingUrl, itemsText }) {
  const norm = String(status || '').toLowerCase().trim();
  const nameGreeting = customerName && customerName !== 'WhatsApp Customer' ? `Hi ${customerName}, ` : 'Hi, ';

  // 1. Shipped / Dispatched
  if (norm === 'shipped' || norm === 'dispatched' || norm === 'in transit' || norm === 'in_transit' || norm === 'out for delivery') {
    let msg = `🚚 *Your Order #${orderNumber} Has Been Shipped!*\n\n` +
      `${nameGreeting}great news! Your package is on its way to you.\n\n`;

    if (courier) {
      msg += `📦 *Courier Partner:* ${courier}\n`;
    }
    if (trackingNumber) {
      msg += `🔖 *Tracking / AWB No:* ${trackingNumber}\n`;
    }
    if (trackingUrl && /^https?:\/\//i.test(trackingUrl)) {
      msg += `🔗 *Live Tracking Link:*\n👉 ${trackingUrl}\n`;
    }

    msg += `\nExpected delivery within 3-5 business days. Thank you for shopping with us! 🙏`;
    return msg;
  }

  // 2. Delivered
  if (norm === 'delivered' || norm === 'completed') {
    return (
      `🎉 *Order Delivered!*\n\n` +
      `${nameGreeting}your order *#${orderNumber}* has been successfully delivered.\n\n` +
      `We hope you love your products! If you need any support, feel free to reply right here in this chat. ⭐`
    );
  }

  // 3. Processing / Packed / Confirmed
  if (norm === 'processing' || norm === 'packed' || norm === 'packing' || norm === 'confirmed') {
    let msg = `⏳ *Order Update: Processing*\n\n` +
      `${nameGreeting}your order *#${orderNumber}* is confirmed and currently being packed for dispatch.\n\n`;
    if (itemsText) {
      msg += `📋 *Items:*\n${itemsText}\n\n`;
    }
    msg += `We will send you live tracking details as soon as the package ships! 🚚`;
    return msg;
  }

  // 4. Cancelled
  if (norm === 'cancelled' || norm === 'canceled') {
    return (
      `⚠️ *Order Update: Cancelled*\n\n` +
      `${nameGreeting}your order *#${orderNumber}* has been cancelled.\n\n` +
      `If you have questions or would like to re-order, please reply to this chat.`
    );
  }

  // 5. Default generic status update
  return (
    `📦 *Order Update: #${orderNumber}*\n\n` +
    `${nameGreeting}your order status has been updated to: *${status.toUpperCase()}*.\n\n` +
    (trackingNumber ? `🔖 *Tracking:* ${trackingNumber}\n` : '') +
    (trackingUrl ? `🔗 *Track:* ${trackingUrl}\n\n` : '\n') +
    `Thank you for your patience! 🙏`
  );
}

// ─── POST /api/orders/sheet-status-update ───────────────────────────────────
router.post('/sheet-status-update', async (req, res) => {
  await ensureOrdersTable();

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  const orderNumber = String(body.order_number || body.orderId || '').trim();
  const rawStatus = String(body.status || '').trim();
  const courier = String(body.courier || body.courier_name || '').trim();
  const trackingNumber = String(body.tracking_number || body.trackingNumber || body.awb || '').trim();
  const trackingUrl = String(body.tracking_url || body.trackingUrl || body.tracking_link || '').trim();
  const customMessage = String(body.custom_message || '').trim();
  const phoneFallback = cleanPhone(body.phone || body.contact_number);
  const nameFallback = String(body.customer_name || body.name || '').trim();

  if (!orderNumber && !phoneFallback) {
    return res.status(400).json({ error: 'order_number or phone is required' });
  }
  if (!rawStatus && !customMessage) {
    return res.status(400).json({ error: 'status or custom_message is required' });
  }

  console.log(`[order-status] Received update for Order #${orderNumber || 'unknown'}: status="${rawStatus}", courier="${courier}", tracking="${trackingNumber}"`);

  try {
    // 1. Look up existing order in DB
    let order = null;
    if (orderNumber) {
      const { rows } = await pool.query(
        `SELECT * FROM coexistence.orders WHERE order_number = $1 LIMIT 1`,
        [orderNumber]
      );
      if (rows.length > 0) order = rows[0];
    }

    const targetPhone = order?.contact_number || phoneFallback;
    const targetName = order?.contact_name || nameFallback || 'Customer';
    const waNumber = order?.wa_number || null;

    if (!targetPhone) {
      console.warn(`[order-status] No contact phone number found for order ${orderNumber}`);
      return res.status(404).json({ error: `No phone number found for order #${orderNumber}` });
    }

    // 2. Update order record in DB if exists
    if (orderNumber) {
      await pool.query(
        `UPDATE coexistence.orders
            SET status = COALESCE(NULLIF($1, ''), status),
                courier = COALESCE(NULLIF($2, ''), courier),
                tracking_number = COALESCE(NULLIF($3, ''), tracking_number),
                tracking_url = COALESCE(NULLIF($4, ''), tracking_url),
                updated_at = NOW()
          WHERE order_number = $5`,
        [rawStatus, courier, trackingNumber, trackingUrl, orderNumber]
      );
    }

    // 3. Find active WhatsApp account
    let acctQuery = `SELECT id FROM coexistence.whatsapp_accounts WHERE is_active = true`;
    const params = [];
    if (waNumber) {
      acctQuery += ` AND wa_number = $1`;
      params.push(waNumber);
    }
    acctQuery += ` ORDER BY id ASC LIMIT 1`;

    const { rows: acctRows } = await pool.query(acctQuery, params);
    if (acctRows.length === 0) {
      console.warn('[order-status] No active WhatsApp account found in system');
      return res.status(500).json({ error: 'No active WhatsApp account configured' });
    }
    const accountId = acctRows[0].id;

    // 4. Construct message text
    let messageText = customMessage;
    if (!messageText) {
      let itemsText = '';
      if (order?.items) {
        try {
          const items = Array.isArray(order.items) ? order.items : JSON.parse(order.items);
          itemsText = items.map(i => `• ${i.quantity || 1}x ${i.title || i.name || 'Item'}`).join('\n');
        } catch {}
      }

      messageText = buildStatusMessage({
        status: rawStatus,
        orderNumber: orderNumber || 'N/A',
        customerName: targetName,
        courier: courier || order?.courier || '',
        trackingNumber: trackingNumber || order?.tracking_number || '',
        trackingUrl: trackingUrl || order?.tracking_url || '',
        itemsText,
      });
    }

    // 5. Save to chat_history and enqueue WhatsApp message
    const localId = `order-status-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    await pool.query(
      `INSERT INTO coexistence.chat_history
         (message_id, phone_number_id, wa_number, contact_number, to_number,
          direction, message_type, message_body, status, timestamp)
       SELECT $1, phone_number_id, wa_number, $2, $2,
              'outgoing', 'text', $3, 'queued', NOW()
         FROM coexistence.whatsapp_accounts WHERE id = $4`,
      [localId, targetPhone, messageText, accountId]
    ).catch(() => {});

    await enqueueSend({
      kind: 'text',
      accountId,
      to: targetPhone,
      localMessageId: localId,
      payload: { body: messageText, previewUrl: true },
    });

    console.log(`[order-status] ✅ WhatsApp status notification queued for ${targetPhone} (Order #${orderNumber}, Status: ${rawStatus})`);

    return res.json({
      success: true,
      order_number: orderNumber,
      status: rawStatus,
      recipient: targetPhone,
      message_sent: true,
    });
  } catch (err) {
    console.error('[order-status] Error processing status update:', err.message);
    return res.status(500).json({ error: err.message });
  }
});

// ─── POST /api/orders/sync-shiprocket ─────────────────────────────────────────
router.post('/sync-shiprocket', async (req, res) => {
  await ensureOrdersTable();
  const { createShiprocketOrder, getShiprocketToken } = require('../services/shiprocket');

  const targetNum = (req.body?.order_number || req.body?.order_id || req.body?.orderNumber || '').trim();

  try {
    const token = await getShiprocketToken();
    if (!token) {
      return res.status(400).json({
        success: false,
        error: 'Shiprocket authentication failed. Please check SHIPROCKET_API_TOKEN in .env',
      });
    }

    if (targetNum) {
      const { rows } = await pool.query(
        `SELECT * FROM coexistence.orders WHERE order_number = $1 LIMIT 1`,
        [targetNum]
      );
      if (rows.length === 0) {
        return res.status(404).json({ success: false, error: `Order ${targetNum} not found in database` });
      }
      const order = rows[0];
      const result = await createShiprocketOrder(order);
      return res.json({ success: !!result?.order_id, order_number: targetNum, result });
    }

    // If no specific order given, sync the most recent orders
    const { rows } = await pool.query(
      `SELECT * FROM coexistence.orders ORDER BY id DESC LIMIT 10`
    );
    const results = [];
    for (const ord of rows) {
      const r = await createShiprocketOrder(ord);
      results.push({ order_number: ord.order_number, success: !!r?.order_id, result: r });
    }
    return res.json({ success: true, synced_count: results.length, results });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

module.exports = router;
