// ============================================================
// Stripe Payment Service
// ============================================================

import type { Order, Product, ApiResponse } from './types';
import { getSupabase } from './db';

function getStripe() {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) return null;
  const Stripe = require('stripe');
  return new Stripe(key);
}

// --- Checkout Session ---

export async function createCheckoutSession(
  contactId: string,
  productId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<ApiResponse<{ checkout_url: string; order_id: string }>> {
  const stripe = getStripe();
  if (!stripe) return { success: false, error: 'Stripe is not configured' };

  const db = getSupabase();
  const { data: product } = await db.from('products').select('*').eq('id', productId).single();
  if (!product) return { success: false, error: 'Product not found' };

  // Create order record
  const { data: order, error: orderErr } = await db.from('orders').insert({
    contact_id: contactId, product_id: productId,
    amount: product.price, currency: product.currency || 'jpy',
    status: 'pending',
  }).select().single();
  if (orderErr) return { success: false, error: orderErr.message };

  const lineItems = [{
    price_data: {
      currency: product.currency || 'jpy',
      product_data: { name: product.name, description: product.description || undefined },
      unit_amount: product.price,
      ...(product.payment_type === 'subscription' ? { recurring: { interval: 'month' as const } } : {}),
    },
    quantity: 1,
  }];

  const sessionParams: any = {
    mode: product.payment_type === 'subscription' ? 'subscription' : 'payment',
    line_items: lineItems,
    success_url: `${successUrl}?order_id=${order.id}&session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: cancelUrl,
    metadata: { order_id: order.id, contact_id: contactId, product_id: productId },
    client_reference_id: contactId,
  };

  // Order bump support
  if (product.order_bump_product_id) {
    const { data: bumpProduct } = await db.from('products').select('*').eq('id', product.order_bump_product_id).single();
    if (bumpProduct) {
      // Add as additional line item (customer can remove at checkout)
      lineItems.push({
        price_data: {
          currency: bumpProduct.currency || 'jpy',
          product_data: { name: `[追加] ${bumpProduct.name}`, description: bumpProduct.description || undefined },
          unit_amount: bumpProduct.price,
          ...(bumpProduct.payment_type === 'subscription' ? { recurring: { interval: 'month' as const } } : {}),
        },
        quantity: 1,
      });
    }
  }

  try {
    const session = await stripe.checkout.sessions.create(sessionParams);

    // Store Stripe session ID
    await db.from('orders').update({ stripe_checkout_session_id: session.id }).eq('id', order.id);

    return { success: true, data: { checkout_url: session.url, order_id: order.id } };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

// --- Webhook Handler ---

export async function handleWebhook(rawBody: string, signature: string): Promise<ApiResponse<null>> {
  const stripe = getStripe();
  if (!stripe) return { success: false, error: 'Stripe is not configured' };

  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) return { success: false, error: 'Webhook secret not configured' };

  let event: any;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err: any) {
    return { success: false, error: `Webhook signature verification failed: ${err.message}` };
  }

  const db = getSupabase();

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object;
      const orderId = session.metadata?.order_id;
      if (orderId) {
        await db.from('orders').update({
          status: 'paid',
          paid_at: new Date().toISOString(),
          stripe_payment_intent_id: session.payment_intent,
          stripe_subscription_id: session.subscription || null,
        }).eq('id', orderId);

        // Auto-enroll in course if product has one
        const { data: order } = await db.from('orders').select('product_id, contact_id').eq('id', orderId).single();
        if (order) {
          const { data: course } = await db.from('courses').select('id').eq('product_id', order.product_id).single();
          if (course) {
            await db.from('enrollments').upsert({
              contact_id: order.contact_id, course_id: course.id,
            }, { onConflict: 'contact_id,course_id' });
          }
        }
      }
      break;
    }

    case 'customer.subscription.deleted': {
      const subscription = event.data.object;
      await db.from('orders').update({ status: 'cancelled' })
        .eq('stripe_subscription_id', subscription.id);
      break;
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object;
      if (invoice.subscription) {
        await db.from('orders').update({ status: 'failed' })
          .eq('stripe_subscription_id', invoice.subscription);
      }
      break;
    }
  }

  return { success: true };
}

// --- Customer Portal ---

export async function createPortalSession(contactId: string, returnUrl: string): Promise<ApiResponse<{ portal_url: string }>> {
  const stripe = getStripe();
  if (!stripe) return { success: false, error: 'Stripe is not configured' };

  const db = getSupabase();
  const { data: orders } = await db.from('orders').select('stripe_subscription_id')
    .eq('contact_id', contactId).not('stripe_subscription_id', 'is', null).limit(1);

  if (!orders?.length) return { success: false, error: 'No active subscriptions found' };

  // Find Stripe customer from subscription
  try {
    const subscription = await stripe.subscriptions.retrieve(orders[0].stripe_subscription_id);
    const session = await stripe.billingPortal.sessions.create({
      customer: subscription.customer,
      return_url: returnUrl,
    });
    return { success: true, data: { portal_url: session.url } };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}
