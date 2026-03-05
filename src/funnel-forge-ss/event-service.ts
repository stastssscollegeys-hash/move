// ============================================================
// Events & Calendar Booking Service
// ============================================================

import type { Event, EventReservation, CalendarSlot, CalendarBooking, ApiResponse } from './types';

import { getSupabase } from './db';

// --- Events ---

export async function listEvents(userId: string): Promise<ApiResponse<Event[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('events').select('*, event_reservations(id)').eq('user_id', userId).order('start_at', { ascending: true });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((e: any) => ({ ...e, reservation_count: (e.event_reservations || []).length })) };
}

export async function createEvent(userId: string, event: Partial<Event>): Promise<ApiResponse<Event>> {
  const db = getSupabase();
  const { data, error } = await db.from('events').insert({
    user_id: userId, name: event.name, description: event.description || '',
    event_type: event.event_type || 'seminar_online',
    venue: event.venue || null, meeting_url: event.meeting_url || null,
    meeting_provider: event.meeting_provider || null,
    start_at: event.start_at, end_at: event.end_at,
    capacity: event.capacity || null, price: event.price || 0,
    product_id: event.product_id || null,
    reminder_config: event.reminder_config || { enabled: false, channels: [], timings: [] },
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getEvent(eventId: string): Promise<ApiResponse<Event>> {
  const db = getSupabase();
  const { data, error } = await db.from('events').select('*').eq('id', eventId).single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateEvent(eventId: string, updates: Partial<Event>): Promise<ApiResponse<Event>> {
  const db = getSupabase();
  const { data, error } = await db.from('events').update(updates).eq('id', eventId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Reservations ---

export async function reserveEvent(eventId: string, contactId: string, orderId?: string): Promise<ApiResponse<EventReservation>> {
  const db = getSupabase();

  // Check capacity
  const { data: event } = await db.from('events').select('capacity').eq('id', eventId).single();
  if (event?.capacity) {
    const { count } = await db.from('event_reservations').select('id', { count: 'exact', head: true }).eq('event_id', eventId).neq('status', 'cancelled');
    if ((count || 0) >= event.capacity) return { success: false, error: '定員に達しています' };
  }

  const paymentStatus = orderId ? 'paid' : (event?.price > 0 ? 'pending' : 'free');
  const receiptNumber = orderId ? `REC-${Date.now().toString(36).toUpperCase()}` : null;

  const { data, error } = await db.from('event_reservations').upsert({
    event_id: eventId, contact_id: contactId,
    payment_status: paymentStatus, order_id: orderId || null,
    receipt_number: receiptNumber,
  }, { onConflict: 'event_id,contact_id' }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function cancelReservation(reservationId: string): Promise<ApiResponse<EventReservation>> {
  const db = getSupabase();
  const { data, error } = await db.from('event_reservations').update({ status: 'cancelled' }).eq('id', reservationId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listReservations(eventId: string): Promise<ApiResponse<EventReservation[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('event_reservations').select('*, contacts(name, email, phone)').eq('event_id', eventId).order('reserved_at');
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function markAttendance(reservationId: string, status: 'attended' | 'no_show'): Promise<ApiResponse<EventReservation>> {
  const db = getSupabase();
  const { data, error } = await db.from('event_reservations').update({ status }).eq('id', reservationId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Calendar Slots ---

export async function listCalendarSlots(userId: string): Promise<ApiResponse<CalendarSlot[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('calendar_slots').select('*').eq('user_id', userId).order('created_at');
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createCalendarSlot(userId: string, slot: Partial<CalendarSlot>): Promise<ApiResponse<CalendarSlot>> {
  const db = getSupabase();
  const { data, error } = await db.from('calendar_slots').insert({
    user_id: userId, name: slot.name, duration_minutes: slot.duration_minutes || 30,
    available_days: slot.available_days || [1, 2, 3, 4, 5],
    available_hours: slot.available_hours || { start: '09:00', end: '18:00' },
    buffer_minutes: slot.buffer_minutes || 15, max_per_day: slot.max_per_day || 8,
    price: slot.price || 0, product_id: slot.product_id || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Calendar Bookings ---

export async function getAvailableSlots(slotId: string, date: string): Promise<ApiResponse<string[]>> {
  const db = getSupabase();
  const { data: slot } = await db.from('calendar_slots').select('*').eq('id', slotId).single();
  if (!slot) return { success: false, error: 'Slot not found' };

  const dayOfWeek = new Date(date).getDay();
  if (!slot.available_days.includes(dayOfWeek)) return { success: true, data: [] };

  // Get existing bookings for the date
  const startOfDay = `${date}T00:00:00`;
  const endOfDay = `${date}T23:59:59`;
  const { data: bookings } = await db.from('calendar_bookings').select('start_at, end_at')
    .eq('slot_id', slotId).neq('status', 'cancelled')
    .gte('start_at', startOfDay).lte('start_at', endOfDay);

  const bookedTimes = new Set((bookings || []).map((b: any) => b.start_at.slice(11, 16)));

  // Generate available times
  const { start, end } = slot.available_hours;
  const [startH, startM] = start.split(':').map(Number);
  const [endH, endM] = end.split(':').map(Number);
  const available: string[] = [];

  let currentMin = startH * 60 + startM;
  const endMin = endH * 60 + endM;
  const step = slot.duration_minutes + slot.buffer_minutes;

  while (currentMin + slot.duration_minutes <= endMin) {
    const timeStr = `${String(Math.floor(currentMin / 60)).padStart(2, '0')}:${String(currentMin % 60).padStart(2, '0')}`;
    if (!bookedTimes.has(timeStr)) available.push(timeStr);
    currentMin += step;
  }

  // Check max per day
  const currentBookings = (bookings || []).length;
  if (currentBookings >= slot.max_per_day) return { success: true, data: [] };

  return { success: true, data: available };
}

export async function bookSlot(slotId: string, contactId: string, startAt: string): Promise<ApiResponse<CalendarBooking>> {
  const db = getSupabase();
  const { data: slot } = await db.from('calendar_slots').select('*').eq('id', slotId).single();
  if (!slot) return { success: false, error: 'Slot not found' };

  const endAt = new Date(new Date(startAt).getTime() + slot.duration_minutes * 60000).toISOString();

  const { data, error } = await db.from('calendar_bookings').insert({
    slot_id: slotId, contact_id: contactId, start_at: startAt, end_at: endAt,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listBookings(userId: string, from?: string, to?: string): Promise<ApiResponse<CalendarBooking[]>> {
  const db = getSupabase();
  let q = db.from('calendar_bookings').select('*, calendar_slots!inner(user_id, name), contacts(name, email)')
    .eq('calendar_slots.user_id', userId).order('start_at');
  if (from) q = q.gte('start_at', from);
  if (to) q = q.lte('start_at', to);
  const { data, error } = await q;
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}
