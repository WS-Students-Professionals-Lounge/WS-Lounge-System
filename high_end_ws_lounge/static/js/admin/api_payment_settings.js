export async function fetchPaymentInfo() {
  const res = await fetch('/api/payment-info', {
    method: 'GET',
    credentials: 'same-origin'
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch payment info (${res.status})`);
  }
  return res.json();
}
