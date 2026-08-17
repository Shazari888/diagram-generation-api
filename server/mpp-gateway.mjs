import http from 'node:http';
import crypto from 'node:crypto';
import { Mppx, stripe, tempo } from 'mppx/server';
import dotenv from 'dotenv';

dotenv.config();

const port = Number(process.env.MPP_PORT || 4242);
const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
const stripeProfileId = process.env.STRIPE_PROFILE_ID;
const tempoCurrency = process.env.TEMPO_CURRENCY || '0x20c0000000000000000000000000000000000000';
const tempoRecipient = process.env.TEMPO_RECIPIENT || '0x742d35Cc6634c0532925a3b844bC9e7595F8fE00';

if (!stripeSecretKey) {
  throw new Error('STRIPE_SECRET_KEY is required to start the MPP gateway.');
}

if (!stripeProfileId) {
  throw new Error('STRIPE_PROFILE_ID is required to start the MPP gateway.');
}

const mppSecretKey = crypto
  .createHmac('sha256', stripeSecretKey)
  .update('mpp-challenge-signing')
  .digest('base64');

const stripeMppx = Mppx.create({
  methods: [
    stripe({
      secretKey: stripeSecretKey,
      networkId: stripeProfileId,
      paymentMethodTypes: ['card', 'link'],
    }),
  ],
  secretKey: mppSecretKey,
});

const tempoMppx = Mppx.create({
  methods: [
    tempo.charge({
      currency: tempoCurrency,
      recipient: tempoRecipient,
      decimals: 18,
    }),
  ],
  secretKey: mppSecretKey,
});

const mergedMppx = Mppx.compose(
  stripeMppx.charge({
    amount: process.env.MPP_STRIPE_AMOUNT || '0.50',
    currency: 'usd',
    decimals: 2,
    networkId: stripeProfileId,
    paymentMethodTypes: ['card', 'link'],
  }),
  tempoMppx.charge({
    amount: process.env.MPP_TEMPO_AMOUNT || '0.01',
    currency: tempoCurrency,
    recipient: tempoRecipient,
    decimals: 18,
  }),
);

function readRequestBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];

    request.on('data', (chunk) => chunks.push(chunk));
    request.on('end', () => resolve(Buffer.concat(chunks).toString()));
    request.on('error', reject);
  });
}

async function handlePayment(request) {
  const url = new URL(request.url);
  const method = url.searchParams.get('method') || url.pathname.replace(/^\/paid\/?/, '').split('/')[0];

  if (method === 'tempo') {
    return tempoMppx.charge({
      amount: process.env.MPP_TEMPO_AMOUNT || '0.01',
      currency: tempoCurrency,
      recipient: tempoRecipient,
      decimals: 18,
    })(request);
  }

  if (method === 'stripe') {
    return stripeMppx.charge({
      amount: process.env.MPP_STRIPE_AMOUNT || '0.50',
      currency: 'usd',
      decimals: 2,
      networkId: stripeProfileId,
      paymentMethodTypes: ['card', 'link'],
    })(request);
  }

  return mergedMppx(request);
}

function resultToHttpResponse(result) {
  if (result && result.status === 402 && result.challenge) {
    return result.challenge;
  }

  return result;
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
    res.end(
      'MPP gateway for the diagram generation API. Use /paid/stripe for fiat and /paid/tempo for crypto.'
    );
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
              amount: String(process.env.MPP_STRIPE_AMOUNT || '50'),
              currency: 'usd',
              intent: 'charge',
              method: 'stripe',
            },
            requestBody: {
              content: { 'application/json': { schema: { type: 'object' } } },
            },
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

  if (req.method === 'POST' && (url.pathname === '/paid' || url.pathname === '/paid/stripe' || url.pathname === '/paid/tempo')) {
    const bodyText = await readRequestBody(req);
    const request = new Request(`http://${req.headers.host || 'localhost'}${req.url}`, {
      method: req.method,
      headers: req.headers,
      body: bodyText,
    });

    const response = resultToHttpResponse(await handlePayment(request));
    const responseHeaders = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    res.writeHead(response.status, responseHeaders);
    const body = await response.text();
    res.end(body);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(port, () => {
  console.log(`MPP gateway listening on http://localhost:${port}`);
});
