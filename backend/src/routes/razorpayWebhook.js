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

const router = Router();

// ─── Signature Verification ─────────────────────────────────────────────────
function verifyRazorpaySignature(rawBody, signature, secret) {
  if (!secret || !signature) return false;
  try {
    const expected = crypto
      .createHmac('sha256', secret)
      .update(rawBody)
      .digest('hex');
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
  } catch {
    return false;
  }
}

// ─── Helper: enqueue WhatsApp text message ───────────────────────────────────
async function sendWhatsAppConfirmation({ waNumber, contactNumber, orderNumber, totalAmount, paymentId }) {
  try {
    // Find the WhatsApp account for this wa_number
    const { rows: acctRows } = await pool.query(
      `SELECT id FROM coexistence.whatsapp_accounts
        WHERE wa_number = $1 AND is_active = true
        LIMIT 1`,
      [waNumber]
    );
    if (acctRows.length === 0) {
      console.warn(`[razorpay-webhook] No active WA account found for wa_number=${waNumber}`);
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
  // rawBody is attached by express.raw() middleware (see app.js / server.js)
  const rawBody = req.rawBody || JSON.stringify(req.body);
  const signature = req.headers['x-razorpay-signature'] || '';
  const webhookSecret = (process.env.RAZORPAY_WEBHOOK_SECRET || '').trim();

  // Verify signature if secret is configured
  if (webhookSecret) {
    if (!verifyRazorpaySignature(rawBody, signature, webhookSecret)) {
      console.warn('[razorpay-webhook] Invalid signature — request rejected');
      return res.status(400).json({ error: 'Invalid signature' });
    }
  } else {
    console.warn('[razorpay-webhook] RAZORPAY_WEBHOOK_SECRET not set — skipping signature check');
  }

  let event;
  try {
    event = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  const eventType = event?.event;
  console.log(`[razorpay-webhook] Received event: ${eventType}`);

  // ── payment_link.paid ────────────────────────────────────────────────────
  if (eventType === 'payment_link.paid') {
    const pl = event?.payload?.payment_link?.entity || {};
    const payment = event?.payload?.payment?.entity || {};

    const paymentLinkId = pl.id;               // plink_XXXX
    const paymentId = payment.id || '';        // pay_XXXX
    const amountPaid = (pl.amount_paid || payment.amount || 0) / 100; // paise → ₹

    if (!paymentLinkId) {
      return res.status(200).json({ status: 'ignored', reason: 'no payment_link id' });
    }

    try {
      // Update order status in DB
      const { rows } = await pool.query(
        `UPDATE coexistence.orders
            SET status = 'paid',
                razorpay_payment_id = $1,
                updated_at = NOW()
          WHERE razorpay_payment_link_id = $2
          RETURNING order_number, contact_number, wa_number, total_amount`,
        [paymentId, paymentLinkId]
      );

      if (rows.length === 0) {
        console.warn(`[razorpay-webhook] No order found for payment_link_id=${paymentLinkId}`);
        return res.status(200).json({ status: 'not_found' });
      }

      const order = rows[0];
      console.log(`[razorpay-webhook] Order ${order.order_number} marked PAID (payment: ${paymentId})`);

      // Send WhatsApp confirmation
      if (order.wa_number && order.contact_number) {
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

  // ── payment_link.cancelled / expired ────────────────────────────────────
  if (eventType === 'payment_link.cancelled' || eventType === 'payment_link.expired') {
    const pl = event?.payload?.payment_link?.entity || {};
    const paymentLinkId = pl.id;
    if (paymentLinkId) {
      await pool.query(
        `UPDATE coexistence.orders
            SET status = $1, updated_at = NOW()
          WHERE razorpay_payment_link_id = $2 AND status = 'unpaid'`,
        [eventType === 'payment_link.cancelled' ? 'cancelled' : 'expired', paymentLinkId]
      ).catch(err => console.error('[razorpay-webhook] status update error:', err.message));
      console.log(`[razorpay-webhook] Order with link ${paymentLinkId} marked ${eventType}`);
    }
    return res.status(200).json({ status: 'ok' });
  }

  // All other events — acknowledge but ignore
  return res.status(200).json({ status: 'ignored', event: eventType });
});

module.exports = router;
