/**
 * Razorpay Webhook Handler
 *
 * Receives payment events from Razorpay and:
 *  1. Verifies the X-Razorpay-Signature header (HMAC-SHA256)
 *  2. Marks the matching order as 'paid' in coexistence.orders
 *  3. Sends a WhatsApp payment confirmation message to the customer
 *
 * Setup:
 *  - Add RAZORPAY_WEBHOOK_SECRET to your .env (set in Razorpay Dashboard → Webhooks)
 *  - Register the endpoint in Razorpay Dashboard:
 *      URL: https://your-domain.com/api/razorpay/webhook
 *      Events: payment_link.paid
 */

const { Router } = require('express');
const crypto = require('crypto');
const pool = require('../db');
const { enqueueSend } = require('../queue/sendQueue');
const { getAccountWithToken } = require('./whatsappAccounts');
const { updateOrderPaymentInGoogleSheet } = require('../services/googleSheets');

const router = Router();

// ─── Signature Verification ─────────────────────────────────────────────────
function verifyRazorpaySignature(rawBody, signature, secret) {
  if (!secret || !signature) {
    console.warn(`[razorpay-webhook] Missing secret (${!!secret}) or signature (${!!signature})`);
    return false;
  }
  try {
    const cleanSecret = String(secret).trim().replace(/^["']|["']$/g, '');
    const cleanSig = String(signature).trim();
    const bodyBuffer = Buffer.isBuffer(rawBody) ? rawBody : Buffer.from(String(rawBody), 'utf8');

    const expected = crypto
      .createHmac('sha256', cleanSecret)
      .update(bodyBuffer)
      .digest('hex');

    const expectedBuf = Buffer.from(expected, 'utf8');
    const signatureBuf = Buffer.from(cleanSig, 'utf8');

    if (expectedBuf.length !== signatureBuf.length) {
      console.warn(`[razorpay-webhook] Signature length mismatch (expected: ${expectedBuf.length}, received: ${signatureBuf.length})`);
      return false;
    }

    const isValid = crypto.timingSafeEqual(expectedBuf, signatureBuf);
    if (!isValid) {
      const masked = cleanSecret.length > 4 ? `${cleanSecret.slice(0, 3)}...${cleanSecret.slice(-2)}` : '***';
      console.warn(`[razorpay-webhook] Signature mismatch! The secret in .env (${masked}, len: ${cleanSecret.length}) does not match what is set in Razorpay Dashboard.`);
    }
    return isValid;
  } catch (err) {
    console.error('[razorpay-webhook] Signature verification error:', err.message);
    return false;
  }
}

// ─── Helper: enqueue WhatsApp text message ───────────────────────────────────
async function sendWhatsAppConfirmation({ waNumber, contactNumber, orderNumber, totalAmount, paymentId }) {
  try {
    // Find the WhatsApp account for this wa_number
    let acctQuery = `SELECT id FROM coexistence.whatsapp_accounts WHERE is_active = true`;
    const params = [];
    if (waNumber) {
      acctQuery += ` AND wa_number = $1`;
      params.push(waNumber);
    }
    acctQuery += ` LIMIT 1`;

    const { rows: acctRows } = await pool.query(acctQuery, params);
    if (acctRows.length === 0) {
      console.warn(`[razorpay-webhook] No active WA account found (wa_number=${waNumber})`);
      return;
    }
    const accountId = acctRows[0].id;

    const body =
      `✅ *Payment Confirmed!*\n\n` +
      `Your order *#${orderNumber}* has been paid successfully.\n\n` +
      `💰 *Amount:* ₹${totalAmount}\n` +
      `🔖 *Payment ID:* ${paymentId}\n\n` +
      `Thank you for your purchase! We'll process your order shortly. 🙏`;

    // Insert optimistic outgoing chat_history row
    const localId = `rzp-confirm-${paymentId}-${Date.now()}`;
    await pool.query(
      `INSERT INTO coexistence.chat_history
         (message_id, phone_number_id, wa_number, contact_number, to_number,
          direction, message_type, message_body, status, timestamp)
       SELECT $1, phone_number_id, wa_number, $2, $2,
              'outgoing', 'text', $3, 'queued', NOW()
         FROM coexistence.whatsapp_accounts WHERE id = $4`,
      [localId, contactNumber, body, accountId]
    ).catch(() => {}); // non-fatal

    await enqueueSend({
      kind: 'text',
      accountId,
      to: contactNumber,
      localMessageId: localId,
      payload: { body, previewUrl: false },
    });

    console.log(`[razorpay-webhook] WhatsApp confirmation queued for ${contactNumber} (order ${orderNumber})`);
  } catch (err) {
    console.error('[razorpay-webhook] Failed to send WhatsApp confirmation:', err.message);
  }
}

// ─── POST /api/razorpay/webhook ──────────────────────────────────────────────
router.post('/', async (req, res) => {
  const rawBody = req.rawBody || JSON.stringify(req.body);
  const signature = req.headers['x-razorpay-signature'] || '';
  const webhookSecret = (process.env.RAZORPAY_WEBHOOK_SECRET || '').trim().replace(/^["']|["']$/g, '');

  console.log(`[razorpay-webhook] Inbound request from ${req.ip} (hasSignature=${!!signature}, hasSecret=${!!webhookSecret})`);

  // Verify signature if secret is configured
  if (webhookSecret) {
    if (!verifyRazorpaySignature(rawBody, signature, webhookSecret)) {
      console.warn('[razorpay-webhook] Signature verification failed — rejecting request');
      return res.status(400).json({ error: 'Invalid signature' });
    }
  } else {
    console.log('[razorpay-webhook] RAZORPAY_WEBHOOK_SECRET not set in .env — accepting request without verification');
  }

  let event;
  try {
    event = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  const eventType = event?.event;
  console.log(`[razorpay-webhook] Event: ${eventType}`);

  // ── Payment Success Events ──────────────────────────────────────────────
  const paidEvents = ['payment_link.paid', 'payment.captured', 'order.paid'];
  if (paidEvents.includes(eventType)) {
    const pl = event?.payload?.payment_link?.entity || {};
    const payment = event?.payload?.payment?.entity || {};
    const orderEntity = event?.payload?.order?.entity || {};

    const paymentLinkId = pl.id || payment.payment_link_id || null;
    const paymentId = payment.id || pl.payment_id || '';
    const razorpayOrderId = orderEntity.id || payment.order_id || null;

    let orderNumber = pl.notes?.order_number || payment.notes?.order_number || orderEntity.notes?.order_number || null;
    if (!orderNumber) {
      const desc = pl.description || payment.description || '';
      const m = desc.match(/Order #?([A-Za-z0-9_-]+)/i);
      if (m) orderNumber = m[1].toUpperCase();
    }

    console.log(`[razorpay-webhook] Searching order (paymentLinkId=${paymentLinkId}, orderNumber=${orderNumber}, paymentId=${paymentId})`);

    try {
      // Update order status in DB
      const { rows } = await pool.query(
        `UPDATE coexistence.orders
            SET status = 'paid',
                razorpay_payment_id = COALESCE(NULLIF($1, ''), razorpay_payment_id),
                updated_at = NOW()
          WHERE (razorpay_payment_link_id IS NOT NULL AND razorpay_payment_link_id = $2)
             OR (order_number IS NOT NULL AND order_number = $3)
             OR (razorpay_order_id IS NOT NULL AND razorpay_order_id = $4)
          RETURNING *`,
        [paymentId, paymentLinkId, orderNumber, razorpayOrderId]
      );

      if (rows.length === 0) {
        console.warn(`[razorpay-webhook] No matching order found in database (link=${paymentLinkId}, order=${orderNumber})`);
        return res.status(200).json({ status: 'not_found' });
      }

      const order = rows[0];
      console.log(`[razorpay-webhook] ✅ Order ${order.order_number} marked PAID (Payment: ${paymentId})`);

      // Update Google Sheet status to PAID
      updateOrderPaymentInGoogleSheet(order.order_number, 'paid', paymentId).catch(sheetErr => {
        console.error('[razorpay-webhook] Google Sheet update error:', sheetErr.message);
      });

      // Auto-push order to Shiprocket (if credentials configured in .env)
      const { createShiprocketOrder } = require('../services/shiprocket');
      createShiprocketOrder(order).catch(sErr => {
        console.error('[razorpay-webhook] Shiprocket auto-push error:', sErr.message);
      });

      // Send WhatsApp confirmation
      if (order.contact_number) {
        await sendWhatsAppConfirmation({
          waNumber: order.wa_number,
          contactNumber: order.contact_number,
          orderNumber: order.order_number,
          totalAmount: parseFloat(order.total_amount).toFixed(2),
          paymentId,
        });
      }

      return res.status(200).json({ status: 'ok', order_number: order.order_number });
    } catch (err) {
      console.error('[razorpay-webhook] DB update error:', err.message);
      return res.status(500).json({ error: 'Internal error' });
    }
  }

  // ── Payment Cancelled / Expired ─────────────────────────────────────────
  if (eventType === 'payment_link.cancelled' || eventType === 'payment_link.expired') {
    const pl = event?.payload?.payment_link?.entity || {};
    const paymentLinkId = pl.id;
    if (paymentLinkId) {
      const newStatus = eventType === 'payment_link.cancelled' ? 'cancelled' : 'expired';
      const { rows } = await pool.query(
        `UPDATE coexistence.orders
            SET status = $1, updated_at = NOW()
          WHERE razorpay_payment_link_id = $2 AND status = 'unpaid'
          RETURNING order_number`,
        [newStatus, paymentLinkId]
      ).catch(err => {
        console.error('[razorpay-webhook] status update error:', err.message);
        return { rows: [] };
      });
      if (rows && rows.length > 0) {
        updateOrderPaymentInGoogleSheet(rows[0].order_number, newStatus).catch(() => {});
      }
      console.log(`[razorpay-webhook] Order with link ${paymentLinkId} marked ${eventType}`);
    }
    return res.status(200).json({ status: 'ok' });
  }

  // All other events
  return res.status(200).json({ status: 'ignored', event: eventType });
});

module.exports = router;
