import http from 'node:http';
import crypto from 'node:crypto';
import StripeClient from 'stripe';
import { Mppx, stripe } from 'mppx/server';
import dotenv from 'dotenv';

dotenv.config();

const port = Number(process.env.MPP_PORT || 4242);

if (!process.env.STRIPE_SECRET_KEY) throw new Error('STRIPE_SECRET_KEY is required.');
if (!process.env.STRIPE_PROFILE_ID) throw new Error('STRIPE_PROFILE_ID is required.');

const mppSecretKey = crypto
  .createHmac('sha256', process.env.STRIPE_SECRET_KEY)
  .update('mpp-challenge-signing')
  .digest('base64');

// StripeClient available for webhook verification and future use
const stripeClient = new StripeClient(process.env.STRIPE_SECRET_KEY);

const mppx = Mppx.create({
  methods: [
    stripe({
      secretKey: process.env.STRIPE_SECRET_KEY,
      networkId: process.env.STRIPE_PROFILE_ID,
      paymentMethodTypes: ['card', 'link'],
    }),
  ],
  secretKey: mppSecretKey,
});

// Per-route pricing in USD. Only known diagram endpoints are allowed.
const PRICING = {
  '/diagrams/generate/svg': '0.05',
  '/diagrams/generate/png': '0.07',
};

function getRouteAmount(pathname) {
  return PRICING[pathname] ?? null;
}

function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
    req.on('error', reject);
  });
}

async function handlePayment(request) {
  const url = new URL(request.url);
  // Strip the /paid prefix to get the actual diagram route
  const route = url.pathname.replace(/^\/paid/, '') || '/diagrams/generate/svg';
  const amount = getRouteAmount(route);

  if (!amount) {
    return Response.json({ error: 'Not found' }, { status: 404 });
  }

  const response = await mppx.charge({
    amount,
    currency: 'usd',
    decimals: 2,
    networkId: process.env.STRIPE_PROFILE_ID,
    paymentMethodTypes: ['card', 'link'],
  })(request);

  if (response.status === 402) return response.challenge;
  return response.withReceipt(Response.json({ ok: true }));
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  if (req.method === 'GET' && url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, service: 'mpp-gateway' }));
    return;
  }

  if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/api')) {
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('MPP gateway for the diagram generation API.');
    return;
  }

  if (req.method === 'GET' && (url.pathname === '/openapi.json' || url.pathname === '/api/openapi.json')) {
    const doc = {
      openapi: '3.1.0',
      info: { title: 'Diagram Generation API MPP Gateway', version: '1.0.0' },
      paths: {
        '/paid': {
          post: {
            'x-payment-info': {
              amount: '50',
              currency: 'usd',
              intent: 'charge',
              method: 'stripe',
            },
            requestBody: { content: { 'application/json': { schema: { type: 'object' } } } },
            responses: {
              '200': { description: 'Access approved' },
              '402': { description: 'Payment Required' },
            },
          },
        },
      },
    };
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(doc));
    return;
  }

  if (req.method === 'POST' && url.pathname.startsWith('/paid')) {
    const bodyText = await readRequestBody(req);
    const request = new Request(`http://${req.headers.host || 'localhost'}${req.url}`, {
      method: req.method,
      headers: req.headers,
      body: bodyText,
    });

    const response = await handlePayment(request);
    const responseHeaders = {};
    response.headers.forEach((value, key) => { responseHeaders[key] = value; });
    res.writeHead(response.status, responseHeaders);
    res.end(await response.text());
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(port, () => {
  console.log(`MPP gateway listening on http://localhost:${port}`);
});
