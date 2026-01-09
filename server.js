const express = require('express');
const stripe = require('stripe')('sk_test_YOUR_SECRET_KEY'); // Replace with your Stripe secret key
const bodyParser = require('body-parser');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('.')); // Serve static files

// Simple file-based database (replace with real database in production)
const DB_FILE = path.join(__dirname, 'database.json');

// Initialize database
async function initDB() {
    try {
        await fs.access(DB_FILE);
    } catch {
        await fs.writeFile(DB_FILE, JSON.stringify({
            users: [],
            subscriptions: [],
            analytics: [],
            feedback: []
        }));
    }
}

async function readDB() {
    const data = await fs.readFile(DB_FILE, 'utf8');
    return JSON.parse(data);
}

async function writeDB(data) {
    await fs.writeFile(DB_FILE, JSON.stringify(data, null, 2));
}

// Create subscription
app.post('/api/create-subscription', async (req, res) => {
    try {
        const { paymentMethodId, email, name, plan, priceId } = req.body;

        // Create or retrieve customer
        let customer;
        const customers = await stripe.customers.list({ email, limit: 1 });

        if (customers.data.length > 0) {
            customer = customers.data[0];
        } else {
            customer = await stripe.customers.create({
                email,
                name,
                payment_method: paymentMethodId,
                invoice_settings: {
                    default_payment_method: paymentMethodId
                }
            });
        }

        // Attach payment method
        await stripe.paymentMethods.attach(paymentMethodId, {
            customer: customer.id
        });

        // Create subscription with trial
        const subscription = await stripe.subscriptions.create({
            customer: customer.id,
            items: [{ price: priceId }],
            trial_period_days: 14,
            expand: ['latest_invoice.payment_intent']
        });

        // Save to database
        const db = await readDB();
        db.users.push({
            id: customer.id,
            email,
            name,
            plan,
            createdAt: new Date().toISOString()
        });
        db.subscriptions.push({
            id: subscription.id,
            customerId: customer.id,
            plan,
            status: subscription.status,
            trialEnd: new Date(subscription.trial_end * 1000).toISOString(),
            createdAt: new Date().toISOString()
        });
        await writeDB(db);

        // Send welcome email (integrate with your email service)
        await sendWelcomeEmail(email, name, plan);

        res.json({
            subscriptionId: subscription.id,
            customerId: customer.id,
            status: subscription.status
        });

    } catch (error) {
        console.error('Subscription error:', error);
        res.status(400).json({ error: error.message });
    }
});

// Webhook for Stripe events
app.post('/api/webhook', bodyParser.raw({ type: 'application/json' }), async (req, res) => {
    const sig = req.headers['stripe-signature'];
    const webhookSecret = 'whsec_YOUR_WEBHOOK_SECRET'; // Replace with your webhook secret

    let event;
    try {
        event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
    } catch (err) {
        return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    // Handle the event
    switch (event.type) {
        case 'customer.subscription.updated':
            await handleSubscriptionUpdate(event.data.object);
            break;
        case 'customer.subscription.deleted':
            await handleSubscriptionCancellation(event.data.object);
            break;
        case 'invoice.payment_succeeded':
            await handleSuccessfulPayment(event.data.object);
            break;
        case 'invoice.payment_failed':
            await handleFailedPayment(event.data.object);
            break;
    }

    res.json({ received: true });
});

// Analytics tracking endpoint
app.post('/api/track', async (req, res) => {
    try {
        const { event, ...data } = req.body;

        const db = await readDB();
        db.analytics.push({
            event,
            data,
            timestamp: new Date().toISOString(),
            ip: req.ip,
            userAgent: req.headers['user-agent']
        });
        await writeDB(db);

        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get analytics
app.get('/api/analytics', async (req, res) => {
    try {
        const db = await readDB();
        const analytics = calculateAnalytics(db);
        res.json(analytics);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

function calculateAnalytics(db) {
    const now = new Date();
    const last30Days = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    // Filter recent analytics
    const recentEvents = db.analytics.filter(a =>
        new Date(a.timestamp) > last30Days
    );

    // Calculate metrics
    const pageViews = recentEvents.filter(a => a.event === 'page_view').length;
    const ctaClicks = recentEvents.filter(a => a.event === 'cta_click').length;
    const checkouts = recentEvents.filter(a => a.event === 'checkout_start').length;
    const purchases = recentEvents.filter(a => a.event === 'purchase').length;

    const conversionRate = pageViews > 0 ? (purchases / pageViews * 100).toFixed(2) : 0;
    const checkoutConversion = checkouts > 0 ? (purchases / checkouts * 100).toFixed(2) : 0;

    // Calculate revenue
    const totalRevenue = db.subscriptions.reduce((sum, sub) => {
        const planPrices = { starter: 49, growth: 99, scale: 197 };
        return sum + (planPrices[sub.plan] || 0);
    }, 0);

    const mrr = totalRevenue; // Monthly Recurring Revenue

    return {
        pageViews,
        ctaClicks,
        checkouts,
        purchases,
        conversionRate,
        checkoutConversion,
        totalRevenue,
        mrr,
        activeSubscriptions: db.subscriptions.filter(s => s.status === 'active').length,
        trialSubscriptions: db.subscriptions.filter(s => s.status === 'trialing').length,
        totalCustomers: db.users.length
    };
}

// Submit feedback
app.post('/api/feedback', async (req, res) => {
    try {
        const { email, rating, message, type } = req.body;

        const db = await readDB();
        db.feedback.push({
            email,
            rating,
            message,
            type,
            timestamp: new Date().toISOString()
        });
        await writeDB(db);

        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get feedback
app.get('/api/feedback', async (req, res) => {
    try {
        const db = await readDB();
        res.json(db.feedback);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Helper functions
async function handleSubscriptionUpdate(subscription) {
    const db = await readDB();
    const index = db.subscriptions.findIndex(s => s.id === subscription.id);
    if (index !== -1) {
        db.subscriptions[index].status = subscription.status;
        await writeDB(db);
    }
}

async function handleSubscriptionCancellation(subscription) {
    const db = await readDB();
    const index = db.subscriptions.findIndex(s => s.id === subscription.id);
    if (index !== -1) {
        db.subscriptions[index].status = 'canceled';
        db.subscriptions[index].canceledAt = new Date().toISOString();
        await writeDB(db);
    }

    // Send cancellation email
    const user = db.users.find(u => u.id === subscription.customer);
    if (user) {
        await sendCancellationEmail(user.email, user.name);
    }
}

async function handleSuccessfulPayment(invoice) {
    const db = await readDB();
    db.analytics.push({
        event: 'payment_success',
        data: {
            customerId: invoice.customer,
            amount: invoice.amount_paid / 100,
            currency: invoice.currency
        },
        timestamp: new Date().toISOString()
    });
    await writeDB(db);
}

async function handleFailedPayment(invoice) {
    const db = await readDB();
    const user = db.users.find(u => u.id === invoice.customer);

    if (user) {
        await sendPaymentFailedEmail(user.email, user.name);
    }
}

async function sendWelcomeEmail(email, name, plan) {
    // Integrate with email service (SendGrid, Mailgun, etc.)
    console.log(`Welcome email sent to ${email} for ${plan} plan`);

    // Example email content structure:
    const emailData = {
        to: email,
        subject: 'Welcome to AutoFlow! 🎉',
        html: `
            <h1>Welcome aboard, ${name}!</h1>
            <p>You've just started your 14-day free trial of the ${plan} plan.</p>
            <p>Here's how to get started:</p>
            <ol>
                <li>Connect your first income source</li>
                <li>Set up your revenue goals</li>
                <li>Enable smart automation</li>
            </ol>
            <a href="https://yourdomain.com/dashboard">Get Started Now</a>
        `
    };

    // Send via your email provider
    // await emailProvider.send(emailData);
}

async function sendCancellationEmail(email, name) {
    console.log(`Cancellation email sent to ${email}`);
    // Send via your email provider
}

async function sendPaymentFailedEmail(email, name) {
    console.log(`Payment failed email sent to ${email}`);
    // Send via your email provider
}

// Initialize and start server
initDB().then(() => {
    app.listen(PORT, () => {
        console.log(`Server running on port ${PORT}`);
        console.log(`Landing page: http://localhost:${PORT}/product-landing.html`);
        console.log(`Admin dashboard: http://localhost:${PORT}/admin.html`);
    });
});

module.exports = app;
