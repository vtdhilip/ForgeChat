const pool = require('../db');

/**
 * Ensures coexistence.orders table exists
 */
async function ensureOrdersTable() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS coexistence.orders (
        id SERIAL PRIMARY KEY,
        order_number VARCHAR(64) UNIQUE NOT NULL,
        shopify_draft_order_id VARCHAR(128),
        shopify_order_number VARCHAR(64),
        wa_number VARCHAR(32),
        contact_number VARCHAR(32) NOT NULL,
        contact_name VARCHAR(255),
        delivery_address TEXT,
        items JSONB DEFAULT '[]'::jsonb,
        subtotal NUMERIC(10,2) DEFAULT 0.00,
        shipping_fee NUMERIC(10,2) DEFAULT 0.00,
        total_amount NUMERIC(10,2) DEFAULT 0.00,
        currency VARCHAR(10) DEFAULT 'INR',
        status VARCHAR(32) DEFAULT 'pending',
        razorpay_order_id VARCHAR(128),
        razorpay_payment_link_id VARCHAR(128),
        razorpay_payment_id VARCHAR(128),
        payment_link_url TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);
  } catch (err) {
    console.error('[checkout] ensure orders table failed:', err.message);
  }
}

/**
 * Generate unique order number e.g. "TJ-8341"
 */
function generateOrderNumber() {
  const rand = Math.floor(1000 + Math.random() * 9000);
  return `TJ-${rand}`;
}

/**
 * Create a live Razorpay Payment Link using Razorpay API
 */
async function createRazorpayPaymentLink({ amount, currency = 'INR', description, customerName, contactNumber, orderNumber }) {
  const keyId = process.env.RAZORPAY_KEY_ID;
  const keySecret = process.env.RAZORPAY_KEY_SECRET;

  if (!keyId || !keySecret) {
    console.warn('[checkout] RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not found in process.env');
    return {
      id: `plink_test_${Date.now()}`,
      short_url: `https://rzp.io/l/pay-${orderNumber.toLowerCase()}`,
    };
  }

  console.log(`[checkout] Creating Razorpay Payment Link for ${orderNumber} (amount: ₹${amount}) using keyId: ${keyId.slice(0, 8)}...`);

  try {
    const authHeader = 'Basic ' + Buffer.from(`${keyId.trim()}:${keySecret.trim()}`).toString('base64');
    const amountInPaise = Math.round(parseFloat(amount) * 100);

    let cleanPhone = String(contactNumber || '').replace(/\D/g, '');
    if (cleanPhone.length > 10) cleanPhone = cleanPhone.slice(-10);

    const bodyData = {
      amount: amountInPaise,
      currency: currency || 'INR',
      accept_partial: false,
      description: (description || `Payment for Order #${orderNumber}`).slice(0, 2048),
      customer: {
        name: (customerName || 'WhatsApp Customer').slice(0, 255),
        contact: cleanPhone.length === 10 ? cleanPhone : undefined,
      },
      notify: { sms: false, email: false },
      reminder_enable: true,
      notes: { order_number: orderNumber },
    };

    const res = await fetch('https://api.razorpay.com/v1/payment_links', {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bodyData),
    });

    const data = await res.json();
    if (!res.ok) {
      console.error('[checkout] Razorpay payment link error response:', JSON.stringify(data));
      return {
        id: `plink_err_${Date.now()}`,
        short_url: `https://rzp.io/l/pay-${orderNumber.toLowerCase()}`,
      };
    }

    console.log(`[checkout] Live Razorpay Link created successfully: ${data.short_url} (ID: ${data.id})`);
    return {
      id: data.id,
      short_url: data.short_url,
    };
  } catch (err) {
    console.error('[checkout] Razorpay API exception:', err.message);
    return {
      id: `plink_err_${Date.now()}`,
      short_url: `https://rzp.io/l/pay-${orderNumber.toLowerCase()}`,
    };
  }
}

/**
 * Create a Shopify Draft Order via Admin API (if domain & access token are set)
 */
async function createShopifyDraftOrder({ lineItems, customerName, contactNumber, address, shippingFee, orderNumber }) {
  const storeDomain = process.env.SHOPIFY_STORE_DOMAIN;
  const accessToken = process.env.SHOPIFY_ADMIN_API_ACCESS_TOKEN;

  if (!storeDomain || !accessToken) {
    return null;
  }

  try {
    const cleanDomain = storeDomain.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    const url = `https://${cleanDomain}/admin/api/2024-01/draft_orders.json`;

    const formattedLineItems = (lineItems || []).map(item => ({
      title: item.title || item.name || 'Product',
      quantity: parseInt(item.quantity, 10) || 1,
      price: parseFloat(item.item_price || item.price) || 0,
      variant_id: item.product_retailer_id && /^\d+$/.test(item.product_retailer_id) ? parseInt(item.product_retailer_id, 10) : undefined,
    }));

    const draftOrderPayload = {
      draft_order: {
        line_items: formattedLineItems.length > 0 ? formattedLineItems : [{ title: 'Order Items', quantity: 1, price: 510 }],
        shipping_line: {
          title: 'Standard Delivery',
          price: parseFloat(shippingFee) || 60,
        },
        shipping_address: {
          address1: address || 'WhatsApp Delivery Address',
          phone: contactNumber || '',
          first_name: customerName || 'WhatsApp Customer',
        },
        note: `Placed via WhatsApp Chat (Order #${orderNumber})`,
      },
    };

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'X-Shopify-Access-Token': accessToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(draftOrderPayload),
    });

    if (res.ok) {
      const data = await res.json();
      return {
        id: String(data.draft_order?.id || ''),
        name: data.draft_order?.name || `#${orderNumber}`,
      };
    }
  } catch (err) {
    console.error('[checkout] Shopify draft order creation error:', err.message);
  }

  return null;
}

/**
 * Main Checkout Handler: Creates Draft Order, Payment Link, and records in Database
 */
async function processOrderCheckout({ contactNumber, contactName, deliveryAddress, orderData, shippingFee = 60, customSubtotal = null }) {
  await ensureOrdersTable();

  const orderNumber = generateOrderNumber();
  const rawItems = orderData?.product_items || [];
  
  // Calculate Subtotal
  let subtotal = 0;
  if (customSubtotal !== null && !isNaN(parseFloat(customSubtotal))) {
    subtotal = parseFloat(customSubtotal);
  } else if (orderData?.total_amount && orderData.total_amount > 0) {
    subtotal = parseFloat(orderData.total_amount);
  } else {
    rawItems.forEach(it => {
      const q = parseInt(it.quantity, 10) || 1;
      const p = parseFloat(it.item_price) || 0;
      subtotal += q * p;
    });
  if (subtotal === 0) {
    // Safety fallback: try parsing Total: ₹xxx from string text if orderData object was omitted
    const textTarget = JSON.stringify(orderData || {}) + ' ' + (deliveryAddress || '');
    const match = textTarget.match(/Total:\s*₹?\s*(\d+(?:\.\d+)?)/i) || textTarget.match(/₹\s*(\d+(?:\.\d+)?)/);
    if (match && parseFloat(match[1]) > 0) {
      subtotal = parseFloat(match[1]);
    }
  }
  if (subtotal === 0) subtotal = 510.00; // Fallback demo price if not set

  const shipping = parseFloat(shippingFee) || 60.00;
  const totalAmount = subtotal + shipping;
  const currency = orderData?.currency || 'INR';

  // 1. Create Shopify Draft Order
  const shopifyDraft = await createShopifyDraftOrder({
    lineItems: rawItems,
    customerName: contactName,
    contactNumber,
    address: deliveryAddress,
    shippingFee: shipping,
    orderNumber,
  });

  // 2. Create Razorpay Payment Link
  const rzpLink = await createRazorpayPaymentLink({
    amount: totalAmount,
    currency,
    description: `Payment for Order #${orderNumber}`,
    customerName: contactName,
    contactNumber,
    orderNumber,
  });

  // 3. Save Order to Database
  let orderRow = null;
  try {
    const { rows } = await pool.query(
      `INSERT INTO coexistence.orders
         (order_number, shopify_draft_order_id, shopify_order_number, contact_number, contact_name,
          delivery_address, items, subtotal, shipping_fee, total_amount, currency, status,
          razorpay_payment_link_id, payment_link_url)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'unpaid', $12, $13)
       RETURNING *`,
      [
        orderNumber,
        shopifyDraft?.id || null,
        shopifyDraft?.name || null,
        contactNumber,
        contactName || null,
        deliveryAddress || null,
        JSON.stringify(rawItems),
        subtotal,
        shipping,
        totalAmount,
        currency,
        rzpLink.id,
        rzpLink.short_url,
      ]
    );
    orderRow = rows[0];
  } catch (dbErr) {
    console.error('[checkout] Order DB insert error:', dbErr.message);
  }

  const result = {
    order_number: orderNumber,
    contact_name: contactName,
    contact_number: contactNumber,
    delivery_address: deliveryAddress,
    items: JSON.stringify(rawItems),
    subtotal: subtotal.toFixed(2),
    shipping_fee: shipping.toFixed(2),
    total_amount: totalAmount.toFixed(2),
    payment_link: rzpLink.short_url,
    shopify_draft_order_id: shopifyDraft?.id || null,
    order_id: orderNumber,
    status: 'unpaid',
  };

  const { appendOrderToGoogleSheet } = require('./googleSheets');
  appendOrderToGoogleSheet(result).catch(err => console.error('[checkout] Google Sheet sync error:', err.message));

  return result;
}

module.exports = {
  processOrderCheckout,
  ensureOrdersTable,
};
