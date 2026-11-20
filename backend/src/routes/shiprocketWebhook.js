/**
 * Shiprocket Tracking & Status Webhook Handler
 *
 * Receives live tracking updates from Shiprocket when:
 *  - AWB is assigned / Picked Up / In Transit / Out for Delivery / Delivered
 *
 * Automatically:
 *  1. Updates the order in coexistence.orders
 *  2. Updates Google Sheet row with Courier, Tracking No, and Status
 *  3. Sends automated WhatsApp tracking & delivery notifications to customer
 *
 * Webhook URL to configure in Shiprocket: https://crm.thaniq.shop/api/shiprocket/webhook
 */

const { Router } = require('express');
const crypto = require('crypto');
const pool = require('../db');
const { enqueueSend } = require('../queue/sendQueue');
const { updateOrderPaymentInGoogleSheet } = require('../services/googleSheets');
const { ensureOrdersTable } = require('../services/checkout');

const router = Router();

// Constant-time token verification via SHA-256 digests (prevents length timing leaks)
function verifyWebhookToken(suppliedToken, expectedToken) {
  if (!suppliedToken || !expectedToken) return false;
  const hashA = crypto.createHash('sha256').update(String(suppliedToken).trim()).digest();
  const hashB = crypto.createHash('sha256').update(String(expectedToken).trim()).digest();
  return crypto.timingSafeEqual(hashA, hashB);
}

// Helper to format clean phone
function cleanPhone(phone) {
  let p = String(phone || '').replace(/\D/g, '');
  if (p.length === 10) p = '91' + p;
  return p;
}

// ─── POST /api/shiprocket/webhook ───────────────────────────────────────────
router.post('/', async (req, res) => {
  // Webhook Authentication
  const expectedToken = (process.env.SHIPROCKET_WEBHOOK_TOKEN || process.env.LOGISTICS_WEBHOOK_SECRET || '').trim();
  const suppliedToken = req.headers['x-shiprocket-token'] || req.headers['x-api-key'] || req.query.token || (req.headers.authorization ? req.headers.authorization.replace(/^Bearer\s+/i, '') : '');

  if (expectedToken) {
    if (!verifyWebhookToken(suppliedToken, expectedToken)) {
      console.warn('[shiprocket-webhook] Unauthorized webhook call - invalid token');
      return res.status(401).json({ error: 'Unauthorized: invalid webhook token' });
    }
  } else if (process.env.NODE_ENV === 'production') {
    console.warn('[shiprocket-webhook] Webhook secret not configured in production');
    return res.status(503).json({ error: 'Webhook verification unavailable' });
  }

  await ensureOrdersTable();

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  console.log('[shiprocket-webhook] Inbound tracking payload:', JSON.stringify(body));

  const orderNumber = String(body.order_id || body.orderId || body.order_number || '').trim();
  const rawStatus = String(body.current_status || body.status || '').toUpperCase().trim();
  const courier = String(body.courier_name || body.courier || '').trim();
  const awb = String(body.awb || body.awb_code || body.tracking_number || '').trim();
  const trackingUrl = String(body.tracking_url || (awb ? `https://shiprocket.co//tracking/${awb}` : '')).trim();

  if (!orderNumber && !awb) {
    return res.status(200).json({ status: 'ignored', reason: 'no order_id or awb' });
  }

  try {
    // 1. Find matching order in DB
    let order = null;
    const { rows } = await pool.query(
      `SELECT * FROM coexistence.orders
        WHERE (order_number IS NOT NULL AND order_number = $1)
           OR (tracking_number IS NOT NULL AND tracking_number = $2)
        LIMIT 1`,
      [orderNumber, awb]
    );

    if (rows.length > 0) order = rows[0];

    // Normalize Shiprocket status
    let normalizedStatus = 'Shipped';
    if (rawStatus.includes('DELIVERED')) {
      normalizedStatus = 'Delivered';
    } else if (rawStatus.includes('CANCEL')) {
      normalizedStatus = 'Cancelled';
    } else if (rawStatus.includes('OUT FOR DELIVERY')) {
      normalizedStatus = 'Out for Delivery';
    } else if (rawStatus.includes('PICKED') || rawStatus.includes('TRANSIT') || rawStatus.includes('AWB') || rawStatus.includes('SHIPPED')) {
      normalizedStatus = 'Shipped';
    }

    // 2. Update DB
    if (order) {
      await pool.query(
        `UPDATE coexistence.orders
            SET status = $1,
                courier = COALESCE(NULLIF($2, ''), courier),
                tracking_number = COALESCE(NULLIF($3, ''), tracking_number),
                tracking_url = COALESCE(NULLIF($4, ''), tracking_url),
                updated_at = NOW()
          WHERE id = $5`,
        [normalizedStatus, courier, awb, trackingUrl, order.id]
      );
    }

    // 3. Update Google Sheet (Status, Courier, AWB Tracking Number, Tracking URL)
    if (orderNumber) {
      updateOrderPaymentInGoogleSheet(
        orderNumber,
        normalizedStatus,
        order?.razorpay_payment_id || '',
        courier,
        awb,
        trackingUrl
      ).catch(() => {});
    }

    // 4. Send WhatsApp Notification to Customer (via Template to work outside 24h window)
    // Only send notification if order exists in database (prevents arbitrary phone relay)
    if (!order) {
      console.log(`[shiprocket-webhook] Order ${orderNumber || awb} not found in DB - skipping customer notification`);
      return res.status(200).json({ status: 'ok', order_number: orderNumber, current_status: normalizedStatus, order_found: false });
    }

    const targetPhone = order.contact_number;
    const targetName = order.contact_name || body.customer_name || 'Customer';
    const waNumber = order.wa_number || null;

    if (targetPhone) {
      let acctQuery = `SELECT id FROM coexistence.whatsapp_accounts WHERE is_active = true`;
      const params = [];
      if (waNumber) {
        acctQuery += ` AND wa_number = $1`;
        params.push(waNumber);
      }
      acctQuery += ` LIMIT 1`;

      const { rows: acctRows } = await pool.query(acctQuery, params);
      if (acctRows.length > 0) {
        const accountId = acctRows[0].id;
        const { sendShippingNotification, sendDeliveryNotification } = require('../services/orderNotifications');

        if (normalizedStatus === 'Delivered') {
          await sendDeliveryNotification({
            accountId,
            targetPhone,
            targetName,
            orderNumber,
          });
        } else if (normalizedStatus === 'Shipped' || normalizedStatus === 'Out for Delivery') {
          await sendShippingNotification({
            accountId,
            targetPhone,
            targetName,
            orderNumber,
            courier,
            awb,
            trackingUrl,
            status: normalizedStatus,
          });
        }
      }
    }

    return res.status(200).json({ status: 'ok', order_number: orderNumber, current_status: normalizedStatus });
  } catch (err) {
    console.error('[shiprocket-webhook] Error processing webhook:', err.message);
    return res.status(500).json({ error: err.message });
  }
});

module.exports = router;
