const pool = require('../db');

function formatProductItems(product, items) {
  if (product && typeof product === 'string' && !product.trim().startsWith('[')) {
    return product;
  }
  let raw = items || product;
  if (!raw) return '1x LINNDEN Premium Modal Trunks';
  if (typeof raw === 'string') {
    try { raw = JSON.parse(raw); } catch { return raw; }
  }
  if (Array.isArray(raw) && raw.length > 0) {
    return raw.map(it => {
      const qty = parseInt(it.quantity, 10) || 1;
      const name = it.title || it.name || it.product_name || 'LINNDEN Premium Modal Trunks';
      const price = it.item_price || it.price ? ` (₹${it.item_price || it.price})` : '';
      return `${qty}x ${name}${price}`;
    }).join(', ');
  }
  return '1x LINNDEN Premium Modal Trunks';
}

/**
 * Appends a new order row to Google Sheets via Google Apps Script Webhook or direct HTTP webhook.
 */
async function appendOrderToGoogleSheet(order) {
  const webhookUrl = process.env.GOOGLE_SHEET_WEBHOOK_URL || process.env.GOOGLE_SHEETS_WEBHOOK_URL;
  if (!webhookUrl) {
    console.log('[googleSheets] GOOGLE_SHEET_WEBHOOK_URL not set — skipping Google Sheets sync');
    return false;
  }

  try {
    const payload = {
      action: 'append_order',
      date: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
      order_number: order.order_number || order.order_id || '',
      customer_name: order.contact_name || order.name || 'WhatsApp Customer',
      phone: order.contact_number || order.phone || '',
      product_items: formatProductItems(order.product, order.items),
      subtotal: order.subtotal || '0.00',
      shipping: order.shipping_fee || '60.00',
      total_amount: order.total_amount || order.order_total || '0.00',
      delivery_address: order.delivery_address || order.address || '',
      payment_link: order.payment_link || '',
      status: order.status || 'unpaid',
    };

    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      console.log(`[googleSheets] Order #${order.order_number} appended to Google Sheet!`);
      return true;
    } else {
      console.warn(`[googleSheets] Webhook returned HTTP ${res.status}`);
    }
  } catch (err) {
    console.error('[googleSheets] Error appending order to Google Sheet:', err.message);
  }

  return false;
}

/**
 * Updates order status, payment ID, courier, and tracking details in Google Sheet
 */
async function updateOrderPaymentInGoogleSheet(orderNumber, status = 'paid', paymentId = '', courier = '', trackingNumber = '', trackingUrl = '') {
  const webhookUrl = process.env.GOOGLE_SHEET_WEBHOOK_URL || process.env.GOOGLE_SHEETS_WEBHOOK_URL;
  if (!webhookUrl) return false;

  try {
    const payload = {
      action: 'update_status',
      order_number: orderNumber,
      status: status.toUpperCase(),
      payment_id: paymentId || '',
      courier: courier || '',
      tracking_number: trackingNumber || '',
      tracking_url: trackingUrl || '',
      updated_at: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
    };

    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      console.log(`[googleSheets] Order #${orderNumber} updated in Google Sheet (Status: ${status.toUpperCase()}, Courier: ${courier || 'N/A'}, AWB: ${trackingNumber || 'N/A'})`);
      return true;
    } else {
      console.warn(`[googleSheets] Google Sheet status update returned HTTP ${res.status}`);
    }
  } catch (err) {
    console.error('[googleSheets] Error updating order status in Google Sheet:', err.message);
  }

  return false;
}

module.exports = {
  appendOrderToGoogleSheet,
  updateOrderPaymentInGoogleSheet,
};
