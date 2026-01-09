# Complete Setup Guide - AutoFlow Income System

## Step-by-Step Setup Instructions

Follow this guide to get your income generation system up and running.

---

## Phase 1: Initial Setup (Day 1)

### 1. Install Node.js

Download and install Node.js from https://nodejs.org (LTS version recommended)

Verify installation:
```bash
node --version
npm --version
```

### 2. Install Project Dependencies

```bash
cd /path/to/autoflow
npm install
```

This installs:
- Express (web server)
- Stripe (payment processing)
- Body-parser (request handling)
- CORS (cross-origin requests)

### 3. Create Stripe Account

1. Go to https://stripe.com and sign up
2. Complete business verification
3. Get your API keys:
   - Dashboard → Developers → API keys
   - Copy both **Publishable key** and **Secret key**

### 4. Configure Stripe Keys

**In `server.js` (line 2):**
```javascript
const stripe = require('stripe')('sk_test_YOUR_SECRET_KEY_HERE');
```

**In `checkout.html` (line 169):**
```javascript
const stripe = Stripe('pk_test_YOUR_PUBLISHABLE_KEY_HERE');
```

⚠️ **Important**: Use test keys (sk_test_, pk_test_) for testing, live keys (sk_live_, pk_live_) for production.

### 5. Create Stripe Products

1. Go to Stripe Dashboard → Products
2. Create three products:

**Starter Plan:**
- Name: AutoFlow Starter
- Price: $49/month recurring
- Copy the Price ID (starts with "price_")

**Growth Plan:**
- Name: AutoFlow Growth
- Price: $99/month recurring
- Copy the Price ID

**Scale Plan:**
- Name: AutoFlow Scale
- Price: $197/month recurring
- Copy the Price ID

### 6. Update Price IDs

**In `checkout.html` (lines 256-273):**
```javascript
const plans = {
    starter: {
        priceId: 'price_YOUR_STARTER_PRICE_ID',
        // ... rest of config
    },
    growth: {
        priceId: 'price_YOUR_GROWTH_PRICE_ID',
        // ... rest of config
    },
    scale: {
        priceId: 'price_YOUR_SCALE_PRICE_ID',
        // ... rest of config
    }
};
```

### 7. Start the Server

```bash
npm start
```

You should see:
```
Server running on port 3000
Landing page: http://localhost:3000/product-landing.html
Admin dashboard: http://localhost:3000/admin.html
```

### 8. Test the System

1. Visit http://localhost:3000/product-landing.html
2. Click "Start Free Trial"
3. Use Stripe test card: `4242 4242 4242 4242`
4. Expiry: Any future date
5. CVC: Any 3 digits
6. Complete checkout

---

## Phase 2: Webhook Setup (Day 1)

### 1. Install Stripe CLI (for local testing)

Download from: https://stripe.com/docs/stripe-cli

**Mac:**
```bash
brew install stripe/stripe-cli/stripe
```

**Windows:**
Download installer from Stripe docs

### 2. Login to Stripe CLI

```bash
stripe login
```

### 3. Forward Webhooks (for local testing)

```bash
stripe listen --forward-to localhost:3000/api/webhook
```

Copy the webhook signing secret (starts with "whsec_")

### 4. Update Webhook Secret

**In `server.js` (line 72):**
```javascript
const webhookSecret = 'whsec_YOUR_WEBHOOK_SECRET';
```

### 5. Test Webhook

Make a test purchase and verify webhook events are received in terminal.

---

## Phase 3: Analytics Setup (Day 2)

### 1. Google Analytics

1. Go to https://analytics.google.com
2. Create new GA4 property
3. Copy Measurement ID (starts with "G-")

**Update in all HTML files:**
```javascript
gtag('config', 'G-YOUR_MEASUREMENT_ID');
```

Files to update:
- product-landing.html
- ads-landing.html
- checkout.html
- dashboard.html

### 2. Facebook Pixel

1. Go to https://business.facebook.com
2. Events Manager → Create Pixel
3. Copy Pixel ID

**Update in HTML files:**
```javascript
fbq('init', 'YOUR_PIXEL_ID');
```

Files to update:
- product-landing.html
- ads-landing.html
- checkout.html

---

## Phase 4: Email Marketing Setup (Day 2-3)

### Option A: SendGrid (Recommended for developers)

1. Sign up at https://sendgrid.com
2. Create API key
3. Install SendGrid package:
```bash
npm install @sendgrid/mail
```

4. **Add to `server.js`:**
```javascript
const sgMail = require('@sendgrid/mail');
sgMail.setApiKey('YOUR_SENDGRID_API_KEY');

async function sendWelcomeEmail(email, name, plan) {
    const msg = {
        to: email,
        from: 'your@email.com',
        subject: 'Welcome to AutoFlow!',
        html: '<h1>Welcome!</h1><p>...'
    };
    await sgMail.send(msg);
}
```

### Option B: Mailgun

1. Sign up at https://mailgun.com
2. Verify domain
3. Get API key
4. Install package:
```bash
npm install mailgun-js
```

### Option C: ConvertKit (Easiest for non-developers)

1. Sign up at https://convertkit.com
2. Create forms for email capture
3. Set up automated sequences
4. Copy embed codes to your pages

---

## Phase 5: Production Deployment (Day 3-4)

### Option A: DigitalOcean (Recommended)

1. Create droplet (Ubuntu 22.04)
2. SSH into server
3. Install Node.js:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

4. Install PM2:
```bash
sudo npm install -g pm2
```

5. Clone/upload your code
6. Install dependencies:
```bash
npm install --production
```

7. Start with PM2:
```bash
pm2 start server.js
pm2 startup
pm2 save
```

### Option B: Heroku (Easiest)

1. Install Heroku CLI
2. Login:
```bash
heroku login
```

3. Create app:
```bash
heroku create your-app-name
```

4. Set environment variables:
```bash
heroku config:set STRIPE_SECRET_KEY=sk_live_xxx
heroku config:set STRIPE_WEBHOOK_SECRET=whsec_xxx
```

5. Deploy:
```bash
git push heroku main
```

### Option C: AWS / Other Cloud Providers

Follow their Node.js deployment guides.

---

## Phase 6: SSL & Domain Setup (Day 4)

### 1. Get Domain

Purchase from:
- Namecheap
- GoDaddy
- Google Domains

### 2. Point Domain to Server

Add A records:
- `@` → Your server IP
- `www` → Your server IP

### 3. Install SSL Certificate (for DigitalOcean)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 4. Set Up Nginx

```bash
sudo nano /etc/nginx/sites-available/default
```

Add:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Restart Nginx:
```bash
sudo systemctl restart nginx
```

---

## Phase 7: Production Stripe Webhooks (Day 4)

### 1. Create Production Webhook

1. Stripe Dashboard → Webhooks
2. Add endpoint: `https://yourdomain.com/api/webhook`
3. Select events:
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_succeeded
   - invoice.payment_failed
4. Copy signing secret

### 2. Update Production Keys

Update all API keys to live keys (sk_live_, pk_live_)

⚠️ **Critical**: Never commit live keys to Git!

Use environment variables:
```bash
export STRIPE_SECRET_KEY=sk_live_xxx
export STRIPE_WEBHOOK_SECRET=whsec_xxx
```

Or create `.env` file (add to .gitignore):
```
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

## Phase 8: Marketing Launch (Day 5-7)

### 1. Product Hunt Launch

1. Create Product Hunt account
2. Prepare:
   - Logo (240x240px)
   - Screenshots
   - Tagline: "Automate your business and scale to $10k/month"
   - Description
3. Launch on Tuesday or Wednesday (best days)
4. Engage with comments all day

### 2. Social Media

**Twitter:**
- Post launch announcement
- Use hashtags: #SaaS #Entrepreneurship #BusinessAutomation
- Share customer testimonials
- Post tips and insights

**LinkedIn:**
- Write article about business automation
- Post in entrepreneur groups
- Connect with potential customers

### 3. Reddit Marketing

Post in:
- r/Entrepreneur
- r/SideProject
- r/SaaS
- r/startups

**Format:**
- Be transparent (no spam)
- Offer value first
- Share your journey
- Ask for feedback

### 4. Content Marketing

Start blog:
- "How I Built a SaaS to $10k/month"
- "10 Ways to Automate Your Business"
- "Complete Guide to Revenue Tracking"
- Share on Medium, Dev.to, Hashnode

---

## Phase 9: Paid Advertising (Month 2+)

### Facebook Ads Setup

1. Create Business Manager account
2. Add payment method
3. Install pixel (already done)
4. Create campaign:
   - Objective: Conversions
   - Budget: $50/day to start
   - Target: Entrepreneurs, business owners, 25-45
   - Placement: Facebook & Instagram
   - Ad: Use `ads-landing.html`

### Google Ads Setup

1. Create Google Ads account
2. Link to Analytics
3. Create Search campaign:
   - Keywords: "business automation software", "revenue tracking tool"
   - Budget: $50/day
   - Landing page: `ads-landing.html`

### Tracking

Monitor:
- Cost per click (CPC)
- Conversion rate
- Customer acquisition cost (CAC)
- Lifetime value (LTV)

**Goal**: CAC < $50, LTV > $300 (6:1 ratio)

---

## Phase 10: Optimization (Ongoing)

### A/B Testing

Test everything:
- Headlines
- CTAs
- Pricing
- Checkout flow
- Email subject lines

Use:
- Google Optimize (free)
- Optimizely
- VWO

### Conversion Optimization

1. **Speed**: Use PageSpeed Insights
2. **Mobile**: Test on real devices
3. **Trust**: Add testimonials, trust badges
4. **Urgency**: Limited-time offers
5. **Social Proof**: "2,847 users", "Featured in..."

### Customer Feedback

1. Send NPS surveys
2. Interview power users
3. Track support tickets
4. Monitor feedback form
5. Iterate based on data

---

## Troubleshooting

### Webhook not firing

1. Check webhook URL is correct
2. Verify signing secret
3. Check server logs:
```bash
pm2 logs
```
4. Test with Stripe CLI:
```bash
stripe trigger payment_intent.succeeded
```

### Emails not sending

1. Check API key
2. Verify sender email
3. Check spam folder
4. Test with:
```bash
curl -X POST http://localhost:3000/api/test-email
```

### Payment failing

1. Use test mode first
2. Check Stripe dashboard for errors
3. Verify price IDs match
4. Check browser console for errors

### Server crashing

1. Check logs:
```bash
pm2 logs
```
2. Check memory usage:
```bash
pm2 monit
```
3. Restart:
```bash
pm2 restart server
```

---

## Security Checklist

- [ ] Use HTTPS everywhere
- [ ] Validate all inputs
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting
- [ ] Verify webhook signatures
- [ ] Keep dependencies updated
- [ ] Use strong passwords
- [ ] Enable 2FA on all accounts
- [ ] Regular backups
- [ ] Monitor for errors (Sentry)

---

## Success Metrics

Track these weekly:

| Metric | Week 1 | Month 1 | Month 3 | Month 6 |
|--------|--------|---------|---------|---------|
| Signups | 10 | 100 | 500 | 1500 |
| Active Subs | 5 | 50 | 250 | 750 |
| MRR | $495 | $4,950 | $24,750 | $74,250 |
| Daily Revenue | $16 | $165 | $825 | $2,475 |

---

## Next Steps

1. ✅ Complete initial setup
2. ✅ Test payment flow
3. ✅ Deploy to production
4. ✅ Launch marketing
5. ✅ Get first 10 customers
6. ✅ Optimize conversion rate
7. ✅ Scale with paid ads
8. ✅ Reach $1000/day

**You got this! 🚀**

Questions? Refer to README.md or check online resources.
